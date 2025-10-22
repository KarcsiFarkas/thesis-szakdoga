#!/usr/bin/env python3
import argparse
import os
import subprocess
import time
import yaml
import json
import sys
from pathlib import Path

# --- Configuration ---
# Assuming the script runs from the root of thesis-szakdoga
ROOT_DIR = Path(__file__).parent.resolve()
MS_CONFIG_DIR = ROOT_DIR / "ms-config"
MGMT_SYSTEM_DIR = ROOT_DIR / "management-system"
OS_INSTALL_DIR = MGMT_SYSTEM_DIR / "OS_install"
DOCKER_COMPOSE_DIR = MGMT_SYSTEM_DIR / "docker-compose-solution"
SERVICES_JSON_PATH = MGMT_SYSTEM_DIR / "website" / "services.json"

# Global debug flag (set by --debug CLI option)
DEBUG = False


# --- Helper Functions ---

def run_command(command: list[str], cwd: Path, env: dict = None, check: bool = True) -> subprocess.CompletedProcess:
    """Runs a shell command.
    - In normal mode: runs and prints output after completion.
    - In debug mode: streams output line-by-line in real time.
    """
    print(f"\n🚀 Running command: {' '.join(command)} in {cwd}")
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    try:
        if DEBUG:
            # Real-time streaming
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="")
            rc = proc.wait()
            if rc != 0:
                print(f"⚠️ Command finished with error (code {rc})")
                if check:
                    raise subprocess.CalledProcessError(rc, command)
            else:
                print("✅ Command finished successfully.")
            # Build a CompletedProcess-like object for compatibility
            return subprocess.CompletedProcess(command, rc, stdout=None)
        else:
            process = subprocess.run(
                command,
                cwd=cwd,
                env=process_env,
                check=check,  # Raise exception on non-zero exit code if True
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT  # Redirect stderr to stdout
            )
            if process.stdout:
                print(process.stdout)
            if process.returncode != 0:
                print(f"⚠️ Command finished with error (code {process.returncode})")
            else:
                print(f"✅ Command finished successfully.")
            return process
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(command)}")
        if hasattr(e, 'stdout') and e.stdout:
            print(e.stdout)
        raise  # Re-raise the exception to stop execution if check=True
    except FileNotFoundError:
        print(f"❌ Error: Command not found: {command[0]}. Is it installed and in PATH?")
        sys.exit(1)


def load_proxmox_api_token() -> str:
    """Loads the Proxmox API token from environment or proxmox_api.txt.

    Priority:
    1) Environment variable PROXMOX_VE_API_TOKEN
    2) File proxmox_api.txt in the repository root. Supports formats:
       - raw token on a single line
       - PROXMOX_VE_API_TOKEN=... (with or without quotes)
       - export PROXMOX_VE_API_TOKEN=... (with or without quotes)
    """
    token = os.environ.get("PROXMOX_VE_API_TOKEN")
    if token:
        return token.strip().strip('"').strip("'").strip()

    token_file = ROOT_DIR / "proxmox_api.txt"
    if token_file.exists():
        try:
            with open(token_file, 'r', encoding='utf-8') as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Handle export/assignment formats
                    if "PROXMOX_VE_API_TOKEN" in line and "=" in line:
                        # remove optional 'export ' prefix
                        if line.lower().startswith("export "):
                            line = line[7:].strip()
                        # split key/value
                        key, val = line.split("=", 1)
                        if key.strip() == "PROXMOX_VE_API_TOKEN":
                            val = val.strip().strip('"').strip("'")
                            if val:
                                return val
                    # Fallback: treat the line itself as the token
                    return line.strip().strip('"').strip("'")
        except IOError as e:
            print(f"❌ Error reading token file {token_file}: {e}")
            sys.exit(1)

    print("❌ Proxmox API token not found. Set PROXMOX_VE_API_TOKEN env var or create proxmox_api.txt at the repo root.")
    print("   Example (do NOT commit secrets): PROXMOX_VE_API_TOKEN=\"user@realm!tokenid=...\"")
    sys.exit(1)


def lint_configurations(tenant_name: str) -> str:
    """Checks for the existence and basic validity of all required config files."""
    print("🕵️  Performing configuration checks...")
    errors = []

    # Required files and directories
    required_paths = {
        "Tenant General Config": MS_CONFIG_DIR / "tenants" / tenant_name / "general.conf.yml",
        "Tenant Selection Config": MS_CONFIG_DIR / "tenants" / tenant_name / "selection.yml",
        "OS Install VM Specs": OS_INSTALL_DIR / "configs" / "vm_specs.yaml",
        "OS Install Config": OS_INSTALL_DIR / "configs" / "install_config.yaml",
        "OS Install Defaults": OS_INSTALL_DIR / "configs" / "defaults.yaml",
        "Services JSON": SERVICES_JSON_PATH,
        "Proxmox Provisioner": OS_INSTALL_DIR / "provision.py",
        "Docker Compose File": DOCKER_COMPOSE_DIR / "docker-compose.yml",
    }

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
    token_env = os.environ.get("PROXMOX_VE_API_TOKEN")
    token_file = ROOT_DIR / "proxmox_api.txt"
    if not token_env and not token_file.exists():
        errors.append("Missing Proxmox API token. Set PROXMOX_VE_API_TOKEN or create proxmox_api.txt at repo root.")

    if errors:
        print("❌ Validation failed with the following errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("✅ All configuration files are present and valid.")
    return deployment_target


def provision_proxmox_vm(vm_name: str):
    """
    Calls the provision.py script to create and configure the Proxmox VM.
    Assumes Proxmox credentials are set as environment variables (PM_API_TOKEN_ID, etc.)
    """
    print(f"🔧 Starting Proxmox VM provisioning for host: {vm_name}")

    # We specify the host and run all targets (infra, os, post)
    py = sys.executable
    command = [
        py,
        "provision.py",
        "--hosts",
        vm_name,
    ]
    if DEBUG:
        command.append("--debug")

    try:
        token = load_proxmox_api_token()
        env_map = {"PROXMOX_VE_API_TOKEN": token}
        if DEBUG:
            env_map["ORCH_DEBUG"] = "1"
        run_command(command, cwd=OS_INSTALL_DIR, env=env_map)
        print(f"✅ Proxmox VM '{vm_name}' provisioned successfully.")
    except subprocess.CalledProcessError:
        print(f"❌ Failed to provision Proxmox VM '{vm_name}'. Check the output above for errors.")
        sys.exit(1)


def load_tenant_config(tenant_name: str) -> tuple[dict, dict]:
    """Loads general and selection config for a tenant."""
    print(f"🔧 Loading configuration for tenant: {tenant_name}")
    tenant_dir = MS_CONFIG_DIR / "tenants" / tenant_name
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


def generate_dotenv(general_config: dict, selection_config: dict, services_def: dict) -> Path:
    """Generates the .env file for Docker Compose."""
    print("🔧 Generating .env file...")
    dotenv_path = DOCKER_COMPOSE_DIR / ".env"
    env_vars = {}

    # 1. Add general settings
    env_vars["DOMAIN"] = general_config.get("tenant_domain", "example.local")
    env_vars["TIMEZONE"] = general_config.get("timezone", "Etc/UTC")
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

    # 4. Write to .env file
    try:
        with open(dotenv_path, 'w') as f:
            for key, value in env_vars.items():
                # Basic quoting for values with spaces, $, or #
                if any(c in value for c in [' ', '$', '#']):
                    # Escape potential internal quotes and wrap
                    value_escaped = value.replace('"', '\\"')
                    f.write(f'{key}="{value_escaped}"\n')
                else:
                    f.write(f'{key}={value}\n')
        print(f"✅ .env file generated at {dotenv_path}")
        return dotenv_path
    except IOError as e:
        print(f"❌ Error writing .env file: {e}")
        sys.exit(1)


def deploy_services(profiles: list[str], wait_time: int = 0):
    """Deploys specified Docker Compose profiles."""
    if not profiles:
        print("🤷 No profiles specified for deployment.")
        return

    print(f"🔧 Deploying profiles: {', '.join(profiles)}")
    command = ["docker-compose"]
    for profile in profiles:
        command.extend(["--profile", profile])
    command.extend(["up", "-d"])

    run_command(command, cwd=DOCKER_COMPOSE_DIR)

    if wait_time > 0:
        print(f"⏳ Waiting {wait_time} seconds for services to initialize...")
        time.sleep(wait_time)


def generate_traefik_dynamic_config(general_config: dict, selection_config: dict) -> Path:
    """Generates the dynamic configuration file for Traefik."""
    print("🔧 Generating Traefik dynamic configuration...")
    domain = general_config.get("tenant_domain", "example.local")
    traefik_dynamic_dir = DOCKER_COMPOSE_DIR / "traefik" / "dynamic"
    traefik_dynamic_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    config_path = traefik_dynamic_dir / "generated_services.yml"

    traefik_config = {"http": {"routers": {}, "services": {}}}
    selected_services = selection_config.get("services", {})

    # Define MUST-HAVE services even if not explicitly in selection.yml
    # (assuming they are always deployed in core step)
    core_services = ["vaultwarden", "homepage", "tailscale"]  # Add others if needed

    for svc_id, svc_config in selected_services.items():
        if svc_config.get("enabled", False) or svc_id in core_services:
            # Basic assumption: service name in compose matches svc_id
            # and exposes a standard port (e.g., 80, 8080, 3000)
            # This needs refinement based on actual compose definitions
            service_port = "80"  # Default, override based on service
            if svc_id == "homepage": service_port = "3000"
            if svc_id == "vaultwarden": service_port = "80"  # Vaultwarden internal port
            # Add more specific ports...

            router_name = f"{svc_id}-router"
            service_name = f"{svc_id}-service"
            host_rule = f"Host(`{svc_id}.{domain}`)"

            traefik_config["http"]["routers"][router_name] = {
                "rule": host_rule,
                "service": service_name,
                "entryPoints": ["websecure"],
                "tls": {"certResolver": "letsencrypt"}  # Assuming letsencrypt is your resolver
            }
            traefik_config["http"]["services"][service_name] = {
                "loadBalancer": {
                    "servers": [{"url": f"http://{svc_id}:{service_port}"}]  # Assumes service name is DNS resolvable
                }
            }
            print(f"  + Added route for {svc_id}.{domain}")

    try:
        with open(config_path, 'w') as f:
            yaml.dump(traefik_config, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Traefik dynamic config generated at {config_path}")
        return config_path
    except IOError as e:
        print(f"❌ Error writing Traefik config: {e}")
        sys.exit(1)


def restart_traefik():
    """Restarts the Traefik container to pick up new dynamic config."""
    print(f"🔄 Restarting Traefik to apply configuration...")
    # Using 'docker restart' is simpler than compose down/up for a single service
    run_command(["docker", "restart", "traefik"], cwd=DOCKER_COMPOSE_DIR,
                check=False)  # check=False in case it wasn't running
    time.sleep(5)  # Give it a moment to restart
    print(f"✅ Traefik restarted.")


# --- Main Orchestration Logic ---

def main(tenant_name: str):
    """Main execution flow."""
    print(f"✨ Starting deployment process for tenant: {tenant_name} ✨")

    # --- Step 1: Validate Configurations ---
    print("\n--- Step 1: Validating Configurations ---")
    vm_to_provision = lint_configurations(tenant_name)

    # --- Step 2: Provision Proxmox VM ---
    print(f"\n--- Step 2: Provisioning Proxmox VM ({vm_to_provision}) ---")
    provision_proxmox_vm(vm_to_provision)

    # --- Step 3: Docker Deployment ---
    print("\n--- Step 3: Docker Service Deployment ---")
    # --- Step 3a: Load Service Definitions ---
    try:
        with open(SERVICES_JSON_PATH, 'r') as f:
            services_definition = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ Error loading services definition from {SERVICES_JSON_PATH}: {e}")
        sys.exit(1)

    # --- Step 3b: Generate Docker Configuration ---
    general_conf, selection_conf = load_tenant_config(tenant_name)
    generate_dotenv(general_conf, selection_conf, services_definition)

    # --- Step 3c: Deploy Core Services ---
    core_profiles = ["traefik", "vaultwarden", "homepage", "tailscale"]
    print("\n--- Deploying Core Docker Services ---")
    deploy_services(core_profiles, wait_time=30)

    # --- Step 3d: Configure Traefik and Dashboard ---
    print("\n--- Configuring Traefik and Dashboard ---")
    generate_traefik_dynamic_config(general_conf, selection_conf)
    # TODO: Implement generate_homepage_config(general_conf, selection_conf)
    print("🔧 Generating Homepage dashboard configuration... (TODO)")

    restart_traefik()

    print("\n🎉 Deployment process finished! 🎉")
    domain = general_conf.get("tenant_domain", "example.local")
    print("\nAccess services at:")
    print(f"  - Traefik Dashboard: http://localhost:8080 (or https://traefik.{domain} if configured)")
    print(f"  - Homepage: https://homepage.{domain}")
    print(f"  - Vaultwarden: https://vaultwarden.{domain}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full-stack orchestrator for Proxmox and Docker services.")
    parser.add_argument("tenant", help="The name of the tenant configuration to use (e.g., 'test').")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug output and real-time subprocess logs.")
    args = parser.parse_args()

    # Set global DEBUG flag
    DEBUG = args.debug
    if DEBUG:
        print("🐞 Debug mode enabled: streaming subprocess output and verbose logs.")

    main(args.tenant)