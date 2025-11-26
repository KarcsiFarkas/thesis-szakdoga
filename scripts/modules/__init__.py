"""
Orchestration modules for the thesis PaaS deployment system.

This package contains modular components for orchestrating:
- Proxmox VM provisioning
- Docker Compose service deployment
- NixOS flake-based deployment
- Configuration management for multi-tenant setups
"""

__version__ = "1.0.0"

# Import main modules for convenient access
from . import constants
from . import utils
from . import config_manager
from . import proxmox_provisioner
from . import remote_executor
from . import docker_deployer
from . import nix_deployer
from . import nixos_anywhere_deployer
from . import traefik_config
from . import chezmoi_deployer

__all__ = [
    "chezmoi_deployer",
    "constants",
    "utils",
    "config_manager",
    "proxmox_provisioner",
    "remote_executor",
    "docker_deployer",
    "nix_deployer",
    "nixos_anywhere_deployer",
    "traefik_config",
]
