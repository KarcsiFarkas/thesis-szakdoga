"""
Remote command execution via SSH and Mosh.

This module provides intelligent remote execution that prefers Mosh when
available on both ends, falling back to SSH when necessary.
"""

import os
import shlex
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
        ssh_cmd = [
            "ssh",
            *utils.ssh_identity_args(),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", f"ConnectTimeout={constants.SSH_CONNECT_TIMEOUT}",
            remote,
            "command -v mosh-server >/dev/null 2>&1 && echo yes || echo no",
        ]
        proc = utils.run_command(
            ssh_cmd,
            cwd=constants.ROOT_DIR,
            check=False,
            stream_output=False,
        )
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
    identity_args = utils.ssh_identity_args()
    ssh_base = [
        "ssh",
        *identity_args,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", f"ConnectTimeout={constants.SSH_CONNECT_TIMEOUT}",
    ]

    if has_local_mosh() and remote_has_mosh_server(remote):
        print(f"🌐 Using mosh for remote command on {remote}")
        ssh_string = shlex.join(ssh_base)
        env = os.environ.copy()
        env["MOSH_SSH"] = ssh_string
        return utils.run_command(
            ["mosh", remote, "--", "bash", "-lc", remote_cmd],
            cwd=constants.ROOT_DIR,
            check=True,
            env=env,
        )

    print(f"🔌 Falling back to SSH for remote command on {remote}")
    ssh_cmd = ssh_base + ["-t", remote, remote_cmd]
    return utils.run_command(
        ssh_cmd,
        cwd=constants.ROOT_DIR,
        check=True,
    )
