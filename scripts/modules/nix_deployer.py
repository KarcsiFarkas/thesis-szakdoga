"""
NixOS flake deployment and staging.

This module handles:
- Staging of nix-solution directories with selected services
- Flake generation with tenant-specific defaults
- Remote NixOS installation via SSH
"""

import shutil
import sys
import yaml
from pathlib import Path
from typing import List, Optional

from . import constants
from . import utils
from . import remote_executor


def service_id_to_module_filename(service_id: str) -> str:
    """
    Map a service id from selection.yml to an expected module filename.

    Falls back to '<id>.nix' with known special cases.

    Args:
        service_id: Service identifier from selection.yml

    Returns:
        Expected module filename (e.g., "homer.nix")
    """
    base = constants.SERVICE_MODULE_MAPPINGS.get(service_id, service_id)
    return f"{base}.nix"


def stage_nix_solution_for_tenant(tenant_name: str) -> Path:
    """
    Create a minimal nix-solution directory containing only general files
    and selected services, and embed tenant defaults (username, static IP)
    into flake's userConfig default.

    Args:
        tenant_name: Name of the tenant

    Returns:
        Path to the staged directory

    Raises:
        SystemExit: If configuration is invalid or files are missing
    """
    tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant_name
    selection_path = tenant_dir / "selection.yml"
    general_path = tenant_dir / "general.conf.yml"
    nix_src = constants.NIX_SOLUTION_DIR
    services_src = constants.NIX_SERVICES_DIR

    if not selection_path.exists():
        print(f"❌ Selection file not found for tenant '{tenant_name}': {selection_path}")
        sys.exit(1)

    # Load selection.yml
    try:
        with open(selection_path, 'r') as f:
            selection = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"❌ Failed to parse selection.yml: {e}")
        sys.exit(1)

    services_cfg = selection.get("services", {}) or {}
    enabled_ids = [sid for sid, cfg in services_cfg.items() if isinstance(cfg, dict) and cfg.get("enabled")]

    # Load general config (for universal_username and deployment_target)
    general_cfg = {}
    if general_path.exists():
        try:
            with open(general_path, 'r') as f:
                general_cfg = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️ Failed to parse {general_path}: {e}")
    else:
        print(f"⚠️ General config not found: {general_path}")

    deployment_target = str(general_cfg.get("deployment_target", "")).strip()

    # Load install_config.yaml to derive network defaults for the deployment target
    install_cfg = utils.read_install_config()
    vm_cfg = install_cfg.get("installs", {}).get(deployment_target, {}) if deployment_target else {}
    vm_users = vm_cfg.get("users", []) if isinstance(vm_cfg, dict) else []
    vm_net = vm_cfg.get("network", {}) if isinstance(vm_cfg, dict) else {}

    def first_username(users: list) -> str:
        if isinstance(users, list) and users and isinstance(users[0], dict):
            return str(users[0].get("username", "")).strip()
        return ""

    # Username default: universal_username -> first install user -> fallback "nixuser"
    default_username = str(general_cfg.get("universal_username", "")).strip() or first_username(vm_users) or constants.DEFAULT_NIX_USERNAME

    # Network defaults
    addr_cidr = str(vm_net.get("address_cidr", "")).strip()
    address = utils.ip_from_cidr(addr_cidr) if addr_cidr else ""
    prefix = None
    if "/" in addr_cidr:
        try:
            prefix = int(addr_cidr.split("/", 1)[1].strip())
        except Exception:
            prefix = None
    gateway = str(vm_net.get("gateway", "")).strip()
    dns_list = vm_net.get("dns", []) if isinstance(vm_net.get("dns", []), list) else []
    interface = str(vm_net.get("interface", "")).strip()  # optional explicit interface name

    # Build userConfig default in Nix syntax
    # Only include attributes that have values to keep it minimal
    user_cfg_lines = [f'  username = "{utils.nix_escape_string(default_username)}";']

    net_attr_lines: List[str] = []
    if address and prefix is not None:
        net_attr_lines.append(f'    address = "{utils.nix_escape_string(address)}";')
        net_attr_lines.append(f'    prefixLength = {prefix};')
    if gateway:
        net_attr_lines.append(f'    gateway = "{utils.nix_escape_string(gateway)}";')
    if dns_list:
        dns_items = " ".join([f'"{utils.nix_escape_string(x)}"' for x in dns_list if str(x).strip()])
        if dns_items:
            net_attr_lines.append(f'    nameservers = [ {dns_items} ];')
    if interface:
        net_attr_lines.append(f'    interface = "{utils.nix_escape_string(interface)}";')

    user_cfg_default = "{\n" + "\n".join(user_cfg_lines)
    if net_attr_lines:
        user_cfg_default += "\n  network = {\n" + "\n".join(net_attr_lines) + "\n  };"
    user_cfg_default += "\n}"

    # Build list of module files to include
    include_modules: List[Path] = []
    missing: List[str] = []
    for sid in sorted(enabled_ids):
        fname = service_id_to_module_filename(sid)
        candidate = services_src / fname
        if candidate.exists():
            include_modules.append(candidate)
        else:
            missing.append(sid)

    # Prepare staging directory
    staged_root = constants.STAGED_ROOT_DIR / f"nix-solution-{tenant_name}"
    if staged_root.exists():
        shutil.rmtree(staged_root)
    (staged_root / "modules" / "services").mkdir(parents=True, exist_ok=True)

    # Copy general files
    shutil.copy2(nix_src / "install.sh", staged_root / "install.sh")
    # Copy hosts entirely to allow interactive selection; install.sh will prune later
    shutil.copytree(nix_src / "hosts", staged_root / "hosts")
    # Copy common.nix
    shutil.copy2(nix_src / "modules" / "common.nix", staged_root / "modules" / "common.nix")

    # Copy only selected service modules
    for mod_path in include_modules:
        shutil.copy2(mod_path, staged_root / "modules" / "services" / mod_path.name)

    # Compose flake.nix with only selected modules and embedded userConfig default
    module_import_lines = ["        ./hosts/server1/default.nix", "        ./modules/common.nix"]
    for mod_path in include_modules:
        rel = f"./modules/services/{mod_path.name}"
        module_import_lines.append(f"        {rel}")

    # Build flake content safely without f-string brace conflicts
    template = """{
  description = "Declarative PaaS Configuration (staged)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }@inputs: {
    nixosConfigurations.server1 = { userConfig ? <<USERCFG>> }: nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = { inherit inputs userConfig; };
      modules = [
<<MODULES>>
      ];
    };
  };
}
"""
    flake_content = template.replace("<<USERCFG>>", user_cfg_default).replace("<<MODULES>>", "\n".join(module_import_lines))

    with open(staged_root / "flake.nix", "w", encoding="utf-8") as f:
        f.write(flake_content)

    print("📦 Staged nix-solution with the following service modules:")
    for p in include_modules:
        print(f"  - {p.name}")
    if missing:
        print("⚠️ Missing module files for enabled services (skipped):")
        for sid in missing:
            print(f"  - {sid}")

    # Log embedded defaults summary
    print("🧩 Embedded defaults into userConfig:")
    print(f"  - username: {default_username}")
    if address and prefix is not None:
        print(f"  - static IPv4: {address}/{prefix}")
    if gateway:
        print(f"  - gateway: {gateway}")
    if dns_list:
        print(f"  - nameservers: {', '.join(map(str, dns_list))}")
    if interface:
        print(f"  - interface: {interface}")

    return staged_root


def install_nixos_flake_via_ssh(
    vm_name: str,
    ssh_user: str,
    local_nix_dir: Optional[Path] = None
) -> None:
    """
    Copy a nix-solution dir (staged or full) to the remote and run install.sh
    non-interactively.

    Args:
        vm_name: Name of the VM to install on
        ssh_user: SSH username for connection
        local_nix_dir: Optional path to nix-solution directory to copy
                       (defaults to management-system/nix-solution)

    Raises:
        SystemExit: If SSH is unavailable or installation fails
    """
    host, vm_cfg = utils.get_vm_connection_info(vm_name)
    if not host:
        print(f"❌ Could not determine SSH host for VM '{vm_name}'.")
        sys.exit(1)

    if not utils.wait_for_ssh(host, ssh_user):
        sys.exit(1)

    remote = f"{ssh_user}@{host}"

    # Determine which local directory to copy
    src_dir = local_nix_dir if local_nix_dir else constants.NIX_SOLUTION_DIR
    if not src_dir.exists():
        print(f"❌ Local nix-solution directory not found at {src_dir}")
        sys.exit(1)

    # Ensure remote target directory is clean
    utils.run_command([
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        remote, "rm -rf ~/nix-solution && mkdir -p ~"
    ], cwd=constants.ROOT_DIR, check=False)

    # Copy the nix flake directory to home
    utils.run_command([
        "scp", "-r",
        str(src_dir),
        f"{remote}:~/"
    ], cwd=constants.ROOT_DIR)

    # If the directory name is not 'nix-solution', rename it remotely so install.sh path is consistent
    if src_dir.name != "nix-solution":
        utils.run_command([
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            remote, f"rm -rf ~/nix-solution && mv ~/{src_dir.name} ~/nix-solution"
        ], cwd=constants.ROOT_DIR, check=False)

    # Execute the install script with default choices (send an empty line)
    remote_cmd = (
        "set -euo pipefail; "
        "cd ~/nix-solution; chmod +x install.sh; "
        "printf '\n' | ./install.sh"
    )
    # Prefer mosh for the interactive/long-running install.sh session
    remote_executor.run_remote_prefer_mosh(remote, remote_cmd)

    print("🎉 NixOS flake installation complete on remote host.")
