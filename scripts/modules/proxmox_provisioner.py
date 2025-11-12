"""
Proxmox VM provisioning orchestration.

This module handles the provisioning of Proxmox VMs by calling
the provision.py script with appropriate parameters and environment.
"""

import subprocess
import sys
from typing import Optional

from . import constants
from . import utils


def provision_proxmox_vm(vm_name: str, username: str) -> None:
    """
    Call the provision.py script to create and configure the Proxmox VM.

    Assumes Proxmox credentials are set as environment variables
    (PM_API_TOKEN_ID, etc.).

    Args:
        vm_name: Name of the VM/host to provision
        username: Username for SSH access to the provisioned VM

    Raises:
        SystemExit: If provisioning fails
    """
    utils.log_info(f"🔧 Starting Proxmox VM provisioning for host: {vm_name}")

    # We specify the host and run all targets (infra, os, post)
    py = sys.executable
    command = [
        py,
        "provision.py",
        "--hosts",
        vm_name,
        "--username",
        username,
    ]
    if utils.DebugContext.is_debug():
        command.append("--debug")

    try:
        token = utils.load_proxmox_api_token()
        env_map = {constants.ENV_PROXMOX_API_TOKEN: token}
        if utils.DebugContext.is_debug():
            env_map[constants.ENV_ORCH_DEBUG] = "1"
        utils.run_command(command, cwd=constants.OS_INSTALL_DIR, env=env_map)
        utils.log_success(f"Proxmox VM '{vm_name}' provisioned successfully.")
    except subprocess.CalledProcessError:
        utils.log_error(f"Failed to provision Proxmox VM '{vm_name}'. Check the output above for errors.")
        sys.exit(1)
