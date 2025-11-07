"""
Remote command execution via SSH and Mosh.

This module provides intelligent remote execution that prefers Mosh when
available on both ends, falling back to SSH when necessary.
"""

import shutil
import subprocess
from typing import Optional

from . import constants
from . import utils


def has_local_mosh() -> bool:
    """
    Check if mosh is available on the orchestrator machine.

    Returns:
        True if mosh is in PATH, False otherwise
    """
    return shutil.which("mosh") is not None


def remote_has_mosh_server(remote: str) -> bool:
    """
    Check if mosh-server is available on the remote host.

    Args:
        remote: SSH connection string (user@host)

    Returns:
        True if mosh-server is available on remote, False otherwise
    """
    try:
        proc = utils.run_command([
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            remote,
            "command -v mosh-server >/dev/null 2>&1 && echo yes || echo no",
        ], cwd=constants.ROOT_DIR, check=False)
        out = (proc.stdout or "").strip() if hasattr(proc, "stdout") else ""
        return "yes" in out.lower()
    except Exception:
        return False


def run_remote_prefer_mosh(remote: str, remote_cmd: str) -> subprocess.CompletedProcess:
    """
    Execute a remote command preferring mosh if available on both ends.

    Falls back to SSH if mosh is not available. Note: File transfers and
    readiness checks still use SSH/SCP.

    Args:
        remote: SSH connection string (user@host)
        remote_cmd: Command to execute on the remote host

    Returns:
        CompletedProcess instance from the command execution

    Raises:
        subprocess.CalledProcessError: If command fails and check=True
    """
    if has_local_mosh() and remote_has_mosh_server(remote):
        print(f"🌐 Using mosh for remote command on {remote}")
        # Run the command within a login shell for consistent PATH/env
        return utils.run_command(
            ["mosh", remote, "--", "bash", "-lc", remote_cmd],
            cwd=constants.ROOT_DIR,
            check=True
        )
    else:
        print(f"🔌 Falling back to SSH for remote command on {remote}")
        return utils.run_command([
            "ssh", "-t",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            remote, remote_cmd
        ], cwd=constants.ROOT_DIR, check=True)
