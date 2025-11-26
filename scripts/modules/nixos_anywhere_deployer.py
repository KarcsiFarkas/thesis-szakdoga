"""
nixos-anywhere deployment helper.

This module integrates the nixos-anywhere deployment flow into the
Python orchestrator so we can provision NixOS on freshly created VMs
without manual prompts. It prefers the tenant-aware deploy-tenant.sh
wrapper and falls back to the legacy nix flake installer when needed.
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict

from . import constants, utils


class NixosAnywhereDeploymentError(RuntimeError):
    """Raised when the nixos-anywhere deployment cannot complete."""


def _dict(val: Any) -> Dict[str, Any]:
    return val if isinstance(val, dict) else {}


def deploy_with_nixos_anywhere(
    tenant_name: str,
    vm_name: str,
    vm_username: str,
    general_config: dict,
) -> None:
    """
    Deploy NixOS using the nixos-anywhere implementation.

    Args:
        tenant_name: Current tenant name
        vm_name: VM identifier from install_config
        vm_username: SSH username to reach the target
        general_config: Tenant general configuration

    Raises:
        NixosAnywhereDeploymentError: When validation or execution fails
    """

    if not constants.NIXOS_ANYWHERE_FLAKE.exists():
        raise NixosAnywhereDeploymentError(
            f"Missing nixos-anywhere flake at {constants.NIXOS_ANYWHERE_FLAKE}"
        )

    anywhere_cfg = _dict(general_config.get("nixos_anywhere"))
    host_profile = (
        anywhere_cfg.get("host")
        or anywhere_cfg.get("hostname")
        or general_config.get("nixos_anywhere_host")
        or vm_name
    )
    disk_device = anywhere_cfg.get("disk_device")

    host_dir = constants.NIXOS_ANYWHERE_DIR / "hosts" / host_profile
    if not host_dir.exists():
        raise NixosAnywhereDeploymentError(
            f"Host profile '{host_profile}' not found at {host_dir}"
        )

    host_or_ip, _ = utils.get_vm_connection_info(vm_name)
    target_host = anywhere_cfg.get("target") or anywhere_cfg.get("target_host") or host_or_ip
    ssh_user = anywhere_cfg.get("ssh_user") or anywhere_cfg.get("user") or vm_username

    if not target_host:
        raise NixosAnywhereDeploymentError(
            f"Could not determine SSH target for VM '{vm_name}'"
        )

    utils.log_info(
        f"🚀 Running nixos-anywhere for host '{host_profile}' at {ssh_user}@{target_host}"
    )

    if not utils.wait_for_ssh(target_host, ssh_user):
        raise NixosAnywhereDeploymentError(
            f"SSH not reachable for {ssh_user}@{target_host}; aborting nixos-anywhere deploy"
        )

    if not constants.NIXOS_ANYWHERE_DEPLOY_TENANT_SCRIPT.exists():
        raise NixosAnywhereDeploymentError(
            f"Deployment script missing: {constants.NIXOS_ANYWHERE_DEPLOY_TENANT_SCRIPT}"
        )

    cmd = [
        "bash",
        str(constants.NIXOS_ANYWHERE_DEPLOY_TENANT_SCRIPT),
        "--yes",
        "-u",
        ssh_user,
    ]

    identity = utils.get_default_ssh_identity()
    if identity:
        cmd += ["-k", str(identity)]

    if disk_device:
        cmd += ["--disk-device", str(disk_device)]

    if utils.DebugContext.is_debug():
        cmd.append("--debug")

    cmd += [tenant_name, host_profile, target_host]

    try:
        utils.run_command(cmd, cwd=constants.NIXOS_ANYWHERE_DIR)
    except subprocess.CalledProcessError as exc:
        raise NixosAnywhereDeploymentError(
            f"nixos-anywhere deployment failed with exit code {exc.returncode}"
        ) from exc

    utils.log_success("nixos-anywhere deployment completed")
