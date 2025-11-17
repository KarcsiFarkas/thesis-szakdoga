"""
Configuration management and validation for the orchestration system.

This module handles:
- Configuration file validation and linting
- Tenant configuration loading
- .env.old file generation for Docker Compose
- Configuration schema validation
"""

import json
import os
import sys
import yaml
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from . import constants


def lint_configurations(tenant_name: str) -> str:
    """
    Check for the existence and basic validity of all required config files.

    For Docker runtime: requires docker-compose artifacts.
    For Nix runtime: requires nix-solution/install.sh.

    Args:
        tenant_name: Name of the tenant to validate

    Returns:
        The deployment target VM name from tenant configuration

    Raises:
        SystemExit: If validation fails
    """
    print("🕵️  Performing configuration checks...")
    errors = []

    # Always-required files and directories
    tenant_general = constants.MS_CONFIG_DIR / "tenants" / tenant_name / "general.conf.yml"
    tenant_selection = constants.MS_CONFIG_DIR / "tenants" / tenant_name / "selection.yml"
    required_paths = {
        "Tenant General Config": tenant_general,
        "Tenant Selection Config": tenant_selection,
        "OS Install VM Specs": constants.OS_INSTALL_VM_SPECS,
        "OS Install Config": constants.OS_INSTALL_CONFIG,
        "OS Install Defaults": constants.OS_INSTALL_DEFAULTS,
        "Proxmox Provisioner": constants.PROXMOX_PROVISIONER_SCRIPT,
    }

    # Load general config early to decide runtime
    general_config = {}
    if tenant_general.exists():
        with open(tenant_general, 'r') as f:
            general_config = yaml.safe_load(f) or {}
    runtime = str(general_config.get("deployment_runtime", "docker")).lower()

    # Runtime-specific requirements
    if runtime == "docker":
        required_paths.update({
            "Services JSON": constants.SERVICES_JSON_PATH,
            "Docker Compose File": constants.DOCKER_COMPOSE_FILE,
        })
    elif runtime == "nix":
        required_paths.update({
            "Nix Flake Installer": constants.NIX_FLAKE_INSTALLER,
        })

    for name, path in required_paths.items():
        if not path.exists():
            errors.append(f"Missing {name}: {path}")

    if errors:
        print("❌ Validation failed with the following errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Check for deployment target in tenant config
    general_conf_path = required_paths["Tenant General Config"]
    with open(general_conf_path, 'r') as f:
        general_config = yaml.safe_load(f) or {}

    deployment_target = general_config.get("deployment_target")
    if not deployment_target:
        errors.append(f"Missing 'deployment_target' in {general_conf_path}. Cannot determine which VM to provision.")

    # Ensure Proxmox token is available either via env or token file
    token_env = os.environ.get(constants.ENV_PROXMOX_API_TOKEN)
    token_file = constants.PROXMOX_API_TOKEN_FILE
    if not token_env and not token_file.exists():
        errors.append(f"Missing Proxmox API token. Set {constants.ENV_PROXMOX_API_TOKEN} or create proxmox_api.txt at repo root.")

    if errors:
        print("❌ Validation failed with the following errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("✅ All configuration files are present and valid.")
    return deployment_target


def load_tenant_config(tenant_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load general and selection config for a tenant.

    Args:
        tenant_name: Name of the tenant

    Returns:
        Tuple of (general_config, selection_config) dictionaries

    Raises:
        SystemExit: If tenant directory doesn't exist
    """
    print(f"🔧 Loading configuration for tenant: {tenant_name}")
    tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant_name
    general_path = tenant_dir / "general.conf.yml"
    selection_path = tenant_dir / "selection.yml"

    if not tenant_dir.is_dir():
        print(f"❌ Error: Tenant directory not found: {tenant_dir}")
        sys.exit(1)

    general_config = {}
    selection_config = {}

    if general_path.is_file():
        with open(general_path, 'r') as f:
            general_config = yaml.safe_load(f) or {}
    else:
        print(f"⚠️ Warning: General config not found: {general_path}")

    if selection_path.is_file():
        with open(selection_path, 'r') as f:
            selection_config = yaml.safe_load(f) or {}
    else:
        print(f"⚠️ Warning: Selection config not found: {selection_path}")

    if not general_config.get("deployment_runtime") == "docker":
        print(f"⚠️ Warning: Tenant '{tenant_name}' is not configured for 'docker' runtime. Proceeding anyway.")

    print("✅ Tenant configuration loaded.")
    return general_config, selection_config


def generate_dotenv(
    general_config: Dict[str, Any],
    selection_config: Dict[str, Any],
    services_def: Dict[str, Any],
    target_dir: Path | None = None,
) -> Path:
    """
    Generate the .env.old file for Docker Compose based on tenant configuration.

    Args:
        general_config: General tenant configuration
        selection_config: Service selection configuration
        services_def: Services definition from services.json

    Returns:
        Path to the generated .env.old file

    Raises:
        SystemExit: If .env.old file cannot be written
    """
    print("🔧 Generating Docker Compose .env files...")
    compose_dir = target_dir or constants.DOCKER_COMPOSE_DIR
    compose_dir.mkdir(parents=True, exist_ok=True)
    base_env: Dict[str, str] = {}
    example_env = compose_dir / ".env.example"
    if example_env.exists():
        base_env = _read_env_file(example_env)
    dotenv_old_path = compose_dir / ".env.old"
    dotenv_current_path = compose_dir / ".env"
    env_vars = {}

    # 1. Add general settings
    env_vars["DOMAIN"] = general_config.get("tenant_domain", constants.DEFAULT_DOMAIN)
    env_vars["TIMEZONE"] = general_config.get("timezone", constants.DEFAULT_TIMEZONE)
    # Add other general settings as needed by compose file

    # 2. Add service-specific settings based on selection.yml and services.json
    selected_services = selection_config.get("services", {})
    all_service_defs = {s['id']: s for s in services_def.get('services', [])}

    for svc_id, svc_config in selected_services.items():
        if svc_config.get("enabled", False):
            env_vars[f"SERVICE_{svc_id.upper()}_ENABLED"] = "true"  # Mark service as enabled
            service_definition = all_service_defs.get(svc_id)
            if service_definition:
                docker_fields = service_definition.get("docker_fields", [])
                options = svc_config.get("options", {})
                for field in docker_fields:
                    field_name = field.get("name")
                    # Use value from selection.yml options if present, else default from services.json
                    value = options.get(field_name, field.get("default"))
                    if value is not None and field_name:  # Only add if a value exists
                        env_vars[field_name] = str(value)  # Ensure it's a string

    # 3. Add any MUST-HAVE service variables if not already present
    # Example: Ensure Traefik email is set
    if "TRAEFIK_ACME_EMAIL" not in env_vars:
        env_vars["TRAEFIK_ACME_EMAIL"] = f"admin@{env_vars['DOMAIN']}"

    merged_env = base_env.copy()
    merged_env.update(env_vars)

    # 4. Serialize environment entries once
    lines: list[str] = []
    for key, value in merged_env.items():
        if any(c in value for c in [' ', '$', '#']):
            value_escaped = value.replace('"', '\\"')
            lines.append(f'{key}="{value_escaped}"')
        else:
            lines.append(f"{key}={value}")
    content = "\n".join(lines) + "\n"

    # 5. Write both .env.old (for auditing) and .env (for docker-compose)
    try:
        for target in (dotenv_old_path, dotenv_current_path):
            with open(target, 'w') as f:
                f.write(content)
        print(f"✅ .env files generated: {dotenv_current_path} (active), {dotenv_old_path} (backup)")
        return dotenv_current_path
    except IOError as e:
        print(f"❌ Error writing docker env files: {e}")
        sys.exit(1)


def load_services_definition() -> Dict[str, Any]:
    """
    Load the services.json definition file.

    Returns:
        Dictionary containing services definitions

    Raises:
        SystemExit: If services.json cannot be loaded
    """
    try:
        with open(constants.SERVICES_JSON_PATH, 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ Error loading services definition from {constants.SERVICES_JSON_PATH}: {e}")
        sys.exit(1)


def get_deployment_username(general_config: Dict[str, Any], vm_name: str) -> str:
    """
    Determine the SSH username for VM deployment.

    Prefers universal_username from general config, falls back to first user
    in install_config for the VM.

    Args:
        general_config: General tenant configuration
        vm_name: Name of the VM

    Returns:
        Username for SSH connection

    Raises:
        SystemExit: If username cannot be determined
    """
    from . import utils  # Import here to avoid circular dependency

    vm_username = general_config.get("universal_username")
    if not vm_username:
        host_or_ip, vm_cfg = utils.get_vm_connection_info(vm_name)
        users = vm_cfg.get("users", []) if isinstance(vm_cfg, dict) else []
        if users and isinstance(users, list) and isinstance(users[0], dict):
            vm_username = users[0].get("username")
    if not vm_username:
        print(f"❌ Error: could not determine SSH username. Set 'universal_username' in general.conf.yml or define users[].username for '{vm_name}' in install_config.yaml")
        sys.exit(1)
    return vm_username


def _read_env_file(path: Path) -> Dict[str, str]:
    """
    Parse a simple KEY=VALUE .env-style file into a dictionary.
    """
    data: Dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                if not key:
                    continue
                data[key] = val.strip().strip('"')
    except FileNotFoundError:
        return {}
    return data
