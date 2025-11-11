"""
Utility functions for command execution and system operations.

This module provides helper functions for:
- Command execution with debug support
- Proxmox API token loading
- SSH connectivity checks
- IP/CIDR parsing
"""

import os
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Optional

from . import constants


class DebugContext:
    """Context manager for global debug state."""
    _debug = False

    @classmethod
    def set_debug(cls, debug: bool) -> None:
        """Set the global debug flag."""
        cls._debug = debug

    @classmethod
    def is_debug(cls) -> bool:
        """Check if debug mode is enabled."""
        return cls._debug


def run_command(
    command: list[str],
    cwd: Path,
    env: Optional[dict] = None,
    check: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a shell command with optional debug output streaming.

    In normal mode: runs and prints output after completion.
    In debug mode: streams output line-by-line in real time.

    Args:
        command: List of command arguments to execute
        cwd: Working directory for command execution
        env: Optional environment variables to add/override
        check: If True, raise exception on non-zero exit code

    Returns:
        CompletedProcess instance with command results

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
        SystemExit: If command executable is not found
    """
    print(f"\n🚀 Running command: {' '.join(command)} in {cwd}")
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    try:
        if DebugContext.is_debug():
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
    """
    Load the Proxmox API token from environment or proxmox_api.txt.

    Priority:
    1. Environment variable PROXMOX_VE_API_TOKEN
    2. File proxmox_api.txt in the repository root. Supports formats:
       - raw token on a single line
       - PROXMOX_VE_API_TOKEN=... (with or without quotes)
       - export PROXMOX_VE_API_TOKEN=... (with or without quotes)

    Returns:
        The Proxmox API token string

    Raises:
        SystemExit: If token cannot be found or loaded
    """
    token = os.environ.get(constants.ENV_PROXMOX_API_TOKEN)
    if token:
        return token.strip().strip('"').strip("'").strip()

    token_file = constants.PROXMOX_API_TOKEN_FILE
    if token_file.exists():
        try:
            with open(token_file, 'r', encoding='utf-8') as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Handle export/assignment formats
                    if constants.ENV_PROXMOX_API_TOKEN in line and "=" in line:
                        # remove optional 'export ' prefix
                        if line.lower().startswith("export "):
                            line = line[7:].strip()
                        # split key/value
                        key, val = line.split("=", 1)
                        if key.strip() == constants.ENV_PROXMOX_API_TOKEN:
                            val = val.strip().strip('"').strip("'")
                            if val:
                                return val
                    # Fallback: treat the line itself as the token
                    return line.strip().strip('"').strip("'")
        except IOError as e:
            print(f"❌ Error reading token file {token_file}: {e}")
            sys.exit(1)

    print(f"❌ Proxmox API token not found. Set {constants.ENV_PROXMOX_API_TOKEN} env var or create proxmox_api.txt at the repo root.")
    print(f"   Example (do NOT commit secrets): {constants.ENV_PROXMOX_API_TOKEN}=\"user@realm!tokenid=...\"")
    sys.exit(1)


def wait_for_ssh(
    host: str,
    user: str,
    timeout_sec: int = constants.SSH_WAIT_TIMEOUT,
    interval_sec: int = constants.SSH_WAIT_INTERVAL
) -> bool:
    """
    Wait until SSH is reachable on host for user within timeout.

    Uses a simple 'ssh -o BatchMode=yes -o ConnectTimeout=5 user@host true'.

    Args:
        host: Target hostname or IP address
        user: SSH username
        timeout_sec: Maximum time to wait in seconds
        interval_sec: Seconds between connection attempts

    Returns:
        True if SSH becomes available, False if timeout is reached
    """
    print(f"⏳ Waiting for SSH on {user}@{host} (timeout {timeout_sec}s)...")
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            run_command([
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", f"ConnectTimeout={constants.SSH_CONNECT_TIMEOUT}",
                f"{user}@{host}",
                "true",
            ], cwd=constants.ROOT_DIR, check=True)
            print("✅ SSH is available.")
            return True
        except Exception:
            remaining = int(timeout_sec - (time.time() - start))
            print(f"... SSH not ready yet, retrying in {interval_sec}s (remaining ~{remaining}s)")
            time.sleep(interval_sec)
    print("❌ Timed out waiting for SSH.")
    return False


def read_install_config() -> dict:
    """
    Load OS_install/configs/install_config.yaml as a dict.

    Returns:
        Dictionary containing install configuration, or empty dict on error
    """
    cfg_path = constants.OS_INSTALL_CONFIG
    try:
        with open(cfg_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"❌ Unable to read install config at {cfg_path}: {e}")
        return {}


def ip_from_cidr(cidr: str) -> str:
    """
    Extract the IP address part from a CIDR notation.

    Args:
        cidr: Address in CIDR format like '192.168.1.80/24'

    Returns:
        IP address without the prefix length
    """
    if not isinstance(cidr, str):
        return ""
    return cidr.split('/')[0].strip()


def get_vm_connection_info(vm_name: str) -> tuple[str, dict]:
    """
    Return (host_or_ip, vm_cfg) from install_config for vm_name.

    Prefers network.address_cidr IP; falls back to network.hostname;
    last resort returns vm_name.

    Args:
        vm_name: Name of the VM in install_config.yaml

    Returns:
        Tuple of (connection_string, vm_config_dict)
    """
    cfg = read_install_config()
    installs = cfg.get("installs", {})
    vm_cfg = installs.get(vm_name, {}) if isinstance(installs, dict) else {}

    network = vm_cfg.get("network", {}) if isinstance(vm_cfg, dict) else {}
    addr = network.get("address_cidr")
    host_or_ip = ""
    if addr:
        host_or_ip = ip_from_cidr(str(addr))
    if not host_or_ip:
        host_or_ip = str(network.get("hostname", "")).strip()
    if not host_or_ip:
        host_or_ip = vm_name
    return host_or_ip, vm_cfg


def nix_escape_string(s: str) -> str:
    """
    Escape a string for safe inclusion in Nix expressions.

    Args:
        s: String to escape

    Returns:
        Escaped string safe for Nix
    """
    s = s or ""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def ssh_command(
    host: str,
    user: str,
    command: str,
    check: bool = True,
    stream_output: bool = False
) -> subprocess.CompletedProcess:
    """
    Execute a command on a remote host via SSH.

    Args:
        host: Target hostname or IP address
        user: SSH username
        command: Command to execute on remote host
        check: If True, raise exception on non-zero exit code
        stream_output: If True, stream output in real-time

    Returns:
        CompletedProcess instance with command results

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", f"ConnectTimeout={constants.SSH_CONNECT_TIMEOUT}",
        f"{user}@{host}",
        command
    ]

    if stream_output or DebugContext.is_debug():
        print(f"🔧 Executing on {user}@{host}: {command}")
        proc = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        output_lines = []
        for line in proc.stdout:
            print(line, end="")
            output_lines.append(line)
        rc = proc.wait()

        result = subprocess.CompletedProcess(
            ssh_cmd,
            rc,
            stdout=''.join(output_lines),
            stderr=None
        )

        if rc != 0 and check:
            raise subprocess.CalledProcessError(rc, ssh_cmd, result.stdout)

        return result
    else:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            check=check
        )
        return result


def scp_upload(
    host: str,
    user: str,
    source_path: str,
    dest_path: str,
    recursive: bool = False
) -> None:
    """
    Upload a file or directory to a remote host via SCP.

    Args:
        host: Target hostname or IP address
        user: SSH username
        source_path: Local path to upload
        dest_path: Remote destination path
        recursive: If True, upload directories recursively

    Raises:
        subprocess.CalledProcessError: If SCP fails
    """
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
    ]

    if recursive:
        scp_cmd.append("-r")

    scp_cmd.extend([
        source_path,
        f"{user}@{host}:{dest_path}"
    ])

    print(f"📤 Uploading {source_path} to {user}@{host}:{dest_path}")

    result = subprocess.run(
        scp_cmd,
        capture_output=True,
        text=True,
        check=True
    )

    if result.returncode == 0:
        print(f"✅ Upload completed successfully")
    else:
        print(f"❌ Upload failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, scp_cmd, result.stdout, result.stderr)


def scp_download(
    host: str,
    user: str,
    source_path: str,
    dest_path: str,
    recursive: bool = False
) -> None:
    """
    Download a file or directory from a remote host via SCP.

    Args:
        host: Target hostname or IP address
        user: SSH username
        source_path: Remote path to download
        dest_path: Local destination path
        recursive: If True, download directories recursively

    Raises:
        subprocess.CalledProcessError: If SCP fails
    """
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
    ]

    if recursive:
        scp_cmd.append("-r")

    scp_cmd.extend([
        f"{user}@{host}:{source_path}",
        dest_path
    ])

    print(f"📥 Downloading {user}@{host}:{source_path} to {dest_path}")

    result = subprocess.run(
        scp_cmd,
        capture_output=True,
        text=True,
        check=True
    )

    if result.returncode == 0:
        print(f"✅ Download completed successfully")
    else:
        print(f"❌ Download failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, scp_cmd, result.stdout, result.stderr)
