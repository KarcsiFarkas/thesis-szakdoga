"""
Global constants and paths for the orchestration system.

This module centralizes all path definitions and configuration variables
used throughout the deployment pipeline.
"""

from pathlib import Path

# Version information
VERSION = "1.0.0"
SYSTEM_NAME = "Thesis PaaS Orchestration System"

# --- Directory Structure ---
# Assuming the script runs from the root of thesis-szakdoga
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
MS_CONFIG_DIR = ROOT_DIR / "ms-config"
MS_CHEZMOI_DIR = ROOT_DIR / "ms-chezmoi"
MGMT_SYSTEM_DIR = ROOT_DIR / "management-system"
OS_INSTALL_DIR = MGMT_SYSTEM_DIR / "OS_install"
DOCKER_COMPOSE_DIR = MGMT_SYSTEM_DIR / "docker-compose-solution"
SERVICES_JSON_PATH = MGMT_SYSTEM_DIR / "website" / "services.json"
NIX_SOLUTION_DIR = MGMT_SYSTEM_DIR / "nix-solution"
NIX_SERVICES_DIR = NIX_SOLUTION_DIR / "modules" / "services"

# --- Configuration Files ---
PROXMOX_API_TOKEN_FILE = ROOT_DIR / "proxmox_api.txt"
OS_INSTALL_VM_SPECS = OS_INSTALL_DIR / "configs" / "vm_specs.yaml"
OS_INSTALL_CONFIG = OS_INSTALL_DIR / "configs" / "install_config.yaml"
OS_INSTALL_DEFAULTS = OS_INSTALL_DIR / "configs" / "defaults.yaml"
PROXMOX_PROVISIONER_SCRIPT = OS_INSTALL_DIR / "provision.py"
DOCKER_COMPOSE_FILE = DOCKER_COMPOSE_DIR / "docker-compose.yml"
NIX_FLAKE_INSTALLER = NIX_SOLUTION_DIR / "install.sh"

# --- Staging Directory ---
STAGED_ROOT_DIR = ROOT_DIR / ".staged"

# --- Chezmoi Configuration ---
CHEZMOI_SOURCE_DIR = MS_CHEZMOI_DIR
CHEZMOI_SCRIPTS_DIR = MS_CHEZMOI_DIR / "scripts"
CHEZMOI_POST_ANSIBLE_SCRIPT = CHEZMOI_SCRIPTS_DIR / "post-ansible-deploy.sh"

# --- Traefik Configuration ---
TRAEFIK_DYNAMIC_DIR = DOCKER_COMPOSE_DIR / "traefik" / "dynamic"
TRAEFIK_DYNAMIC_CONFIG_FILE = TRAEFIK_DYNAMIC_DIR / "generated_services.yml"

# --- Default Values ---
DEFAULT_TIMEZONE = "Etc/UTC"
DEFAULT_DOMAIN = "example.local"
DEFAULT_NIX_USERNAME = "nixuser"

# --- Core Docker Services ---
CORE_DOCKER_PROFILES = ["traefik", "vaultwarden", "homepage", "tailscale"]
CORE_SERVICES_WAIT_TIME = 30  # seconds to wait after deploying core services

# --- SSH/Connection Settings ---
SSH_CONNECT_TIMEOUT = 5  # seconds
SSH_WAIT_TIMEOUT = 600  # seconds to wait for SSH to become available
SSH_WAIT_INTERVAL = 10  # seconds between SSH connection attempts

# --- Environment Variables ---
ENV_PROXMOX_API_TOKEN = "PROXMOX_VE_API_TOKEN"
ENV_ORCH_DEBUG = "ORCH_DEBUG"

# --- Service Port Mappings (for Traefik configuration) ---
SERVICE_PORT_MAPPINGS = {
    "homepage": "3000",
    "vaultwarden": "80",
    "traefik": "8080",
    # Add more service-specific ports as needed
}

# --- Service ID to Module Filename Mappings ---
# Special cases where service ID doesn't match the module filename
SERVICE_MODULE_MAPPINGS = {
    "homepage": "homer",  # repo uses homer.nix for Homepage dashboard
    # Add more mappings as needed
}
