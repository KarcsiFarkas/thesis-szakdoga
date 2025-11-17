"""
Docker Compose service deployment.

This module handles the deployment of Docker Compose services with
profile-based configuration.
"""

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import constants
from . import utils


def _network_exists(network_name: str) -> bool:
    """
    Check whether a Docker network exists without emitting warnings.
    """
    try:
        result = subprocess.run(
            ["docker", "network", "inspect", network_name],
            cwd=constants.ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError as exc:
        utils.log_error("Docker CLI not found while verifying networks.")
        raise RuntimeError("Docker is required to deploy compose services") from exc

    return result.returncode == 0


def _ensure_network_exists(
    network_name: str,
    *,
    driver: Optional[str] = None,
    attachable: bool = False,
) -> None:
    """
    Ensure the given Docker network exists, creating it if missing.
    """
    if not network_name:
        return

    if _network_exists(network_name):
        utils.log_info(f"✅ Docker network '{network_name}' already exists.")
        return

    utils.log_info(f"🌐 Creating Docker network '{network_name}'")
    command = ["docker", "network", "create"]
    if driver:
        command.extend(["--driver", driver])
    if attachable:
        command.append("--attachable")
    command.append(network_name)
    utils.run_command(command, cwd=constants.ROOT_DIR)


def _ensure_required_networks() -> None:
    """
    Ensure all required Docker networks defined in constants exist.
    """
    network_specs: List[Dict[str, Any]] = getattr(
        constants, "REQUIRED_DOCKER_NETWORKS", []
    )
    if not network_specs:
        return

    for spec in network_specs:
        network_name_raw = spec.get("name")
        if not network_name_raw:
            utils.log_warn("Skipping Docker network spec without a name.")
            continue
        network_name = str(network_name_raw).strip()
        if not network_name:
            utils.log_warn("Skipping Docker network spec with an empty name.")
            continue

        driver_raw = spec.get("driver")
        driver = str(driver_raw).strip() if driver_raw else None
        attachable = bool(spec.get("attachable", False))
        _ensure_network_exists(network_name, driver=driver, attachable=attachable)


def _default_remote_base_dir() -> str:
    """
    Construct the default remote directory used for legacy deployments.
    """
    configured = getattr(constants, "LEGACY_REMOTE_DEPLOY_DIR", "").strip()
    if not configured:
        configured = "paas-docker-runtime"
    if configured.startswith("/"):
        return configured
    return f"~/{configured}"


def _prepare_remote_bundle(
    host: str,
    user: str,
    remote_base: str,
    local_dir: Path,
    *,
    preserve_paths: Optional[List[str]] = None,
) -> str:
    """
    Remove any previous bundle and copy the docker-compose assets to the remote VM.
    """
    remote_parent = remote_base.rstrip("/") or "."
    local_basename = local_dir.name
    final_remote_dir = f"{remote_parent}/{local_basename}"

    preserved_dir = _stash_remote_paths(
        host,
        user,
        final_remote_dir,
        preserve_paths or [],
    )

    cleanup_cmd = (
        f"(rm -rf {final_remote_dir} || sudo rm -rf {final_remote_dir})"
    )
    utils.ssh_command(
        host,
        user,
        f"{cleanup_cmd} && mkdir -p {remote_parent}",
        stream_output=True,
    )

    utils.scp_upload(
        host,
        user,
        str(local_dir),
        f"{remote_parent}/",
        recursive=True,
    )

    if preserved_dir:
        _restore_remote_paths(
            host,
            user,
            final_remote_dir,
            preserved_dir,
            preserve_paths or [],
        )

    return final_remote_dir


def _ensure_remote_networks(host: str, user: str) -> None:
    """
    Ensure all required Docker networks exist on the remote VM.
    """
    network_specs: List[Dict[str, Any]] = getattr(
        constants, "REQUIRED_DOCKER_NETWORKS", []
    )
    if not network_specs:
        return

    for spec in network_specs:
        network_name_raw = spec.get("name")
        if not network_name_raw:
            utils.log_warn("Skipping Docker network spec without a name.")
            continue

        network_name = str(network_name_raw).strip()
        if not network_name:
            utils.log_warn("Skipping Docker network spec with an empty name.")
            continue

        driver_raw = spec.get("driver")
        driver = str(driver_raw).strip() if driver_raw else "bridge"
        attachable = "true" if spec.get("attachable", False) else "false"

        cmd = (
            "set -euo pipefail;"
            f"if docker network inspect {network_name} >/dev/null 2>&1; then exit 0; fi;"
            f"docker network create --driver {driver} "
            f"{'--attachable ' if attachable == 'true' else ''}{network_name}"
        )
        utils.ssh_command(
            host,
            user,
            cmd,
            stream_output=True,
            check=True,
        )


def _compose_command_for_profiles(profiles: List[str]) -> Tuple[str, str]:
    """
    Return the docker compose command string and pretty label.
    """
    profile_args = ""
    if profiles:
        profile_parts = []
        for profile in profiles:
            profile_parts.append(f"--profile {profile}")
        profile_args = " ".join(profile_parts)
    compose_cmd = (
        "set -euo pipefail; "
        "if command -v docker-compose >/dev/null 2>&1; then "
        "COMPOSE_BIN='docker-compose'; "
        "else "
        "COMPOSE_BIN='docker compose'; "
        "fi; "
        f"$COMPOSE_BIN {profile_args} up -d"
    )
    return compose_cmd, profile_args


def deploy_services(profiles: List[str], wait_time: int = 0) -> None:
    """
    Deploy specified Docker Compose profiles.

    Args:
        profiles: List of Docker Compose profile names to deploy
        wait_time: Seconds to wait after deployment for service initialization
    """
    if not profiles:
        print("🤷 No profiles specified for deployment.")
        return

    _ensure_required_networks()

    print(f"🔧 Deploying profiles: {', '.join(profiles)}")
    command = ["docker-compose"]
    for profile in profiles:
        command.extend(["--profile", profile])
    command.extend(["up", "-d"])

    utils.run_command(command, cwd=constants.DOCKER_COMPOSE_DIR)

    if wait_time > 0:
        print(f"⏳ Waiting {wait_time} seconds for services to initialize...")
        time.sleep(wait_time)


def deploy_core_services(wait_time: int = constants.CORE_SERVICES_WAIT_TIME) -> None:
    """
    Deploy core Docker services required for the PaaS infrastructure.

    Core services include Traefik, Vaultwarden, Homepage, and Tailscale.

    Args:
        wait_time: Seconds to wait after deployment for service initialization
    """
    print("\n--- Deploying Core Docker Services ---")
    deploy_services(constants.CORE_DOCKER_PROFILES, wait_time=wait_time)


def deploy_services_remote(
    profiles: List[str],
    host: str,
    user: str,
    wait_time: int = 0,
    remote_base: Optional[str] = None,
    local_compose_dir: Optional[Path] = None,
    preserve_paths: Optional[List[str]] = None,
    restart_services: Optional[List[str]] = None,
) -> None:
    """
    Deploy Docker Compose services on a remote VM via SSH.

    Args:
        profiles: List of Compose profile names to deploy
        host: Remote host/IP
        user: SSH username
        wait_time: Seconds to wait post-deploy
        remote_base: Optional remote directory override for bundle sync
    """
    if not profiles:
        print("🤷 No profiles specified for deployment.")
        return

    base = remote_base or _default_remote_base_dir()
    local_dir = Path(local_compose_dir) if local_compose_dir else constants.DOCKER_COMPOSE_DIR
    utils.log_info(f"📦 Syncing docker-compose bundle to {user}@{host}:{base}")
    remote_compose_dir = _prepare_remote_bundle(
        host,
        user,
        base,
        local_dir,
        preserve_paths=preserve_paths,
    )
    _ensure_remote_networks(host, user)

    compose_cmd, profile_args = _compose_command_for_profiles(profiles)
    profile_display = profile_args or "(all default services)"
    print(f"🔧 Deploying profiles on remote host: {profile_display}")

    remote_command = f"cd {remote_compose_dir} && {compose_cmd}"
    utils.ssh_command(
        host,
        user,
        remote_command,
        stream_output=True,
    )

    if restart_services:
        restart_cmd = (
            "set -euo pipefail; "
            "if command -v docker-compose >/dev/null 2>&1; then "
            "COMPOSE_BIN='docker-compose'; "
            "else "
            "COMPOSE_BIN='docker compose'; "
            "fi; "
            f"$COMPOSE_BIN restart {' '.join(restart_services)}"
        )
        utils.ssh_command(
            host,
            user,
            f"cd {remote_compose_dir} && {restart_cmd}",
            stream_output=True,
        )

    if wait_time > 0:
        print(f"⏳ Waiting {wait_time} seconds for services to initialize on {host}...")
        time.sleep(wait_time)


def deploy_core_services_remote(
    host: str,
    user: str,
    wait_time: int = constants.CORE_SERVICES_WAIT_TIME,
    remote_base: Optional[str] = None,
    local_compose_dir: Optional[Path] = None,
    preserve_paths: Optional[List[str]] = None,
    restart_services: Optional[List[str]] = None,
) -> None:
    """
    Deploy the core service profiles on a remote VM via SSH.
    """
    print("\n--- Deploying Core Docker Services (Remote) ---")
    deploy_services_remote(
        constants.CORE_DOCKER_PROFILES,
        host,
        user,
        wait_time=wait_time,
        remote_base=remote_base,
        local_compose_dir=local_compose_dir,
        preserve_paths=preserve_paths,
        restart_services=restart_services,
    )
def _stash_remote_paths(
    host: str,
    user: str,
    remote_dir: str,
    relative_paths: List[str],
) -> Optional[str]:
    """
    Copy remote paths to a temporary directory so they can be restored later.
    """
    if not relative_paths:
        return None

    try:
        result = utils.ssh_command(
            host,
            user,
            "mktemp -d",
            stream_output=False,
        )
    except subprocess.CalledProcessError:
        return None

    tmp_dir = (result.stdout or "").strip()
    if not tmp_dir:
        return None

    for rel in relative_paths:
        safe_rel = rel.strip().strip("/")
        if not safe_rel:
            continue
        remote_path = f"{remote_dir.rstrip('/')}/{safe_rel}"
        dest_path = f"{tmp_dir}/{safe_rel}"
        cmd = (
            "set -euo pipefail; "
            f"if [ -e {remote_path} ]; then "
            f"mkdir -p $(dirname {dest_path}); "
            f"cp -a {remote_path} {dest_path}; "
            "fi"
        )
        utils.ssh_command(
            host,
            user,
            cmd,
            stream_output=True,
            check=False,
        )

    return tmp_dir


def _restore_remote_paths(
    host: str,
    user: str,
    remote_dir: str,
    tmp_dir: str,
    relative_paths: List[str],
) -> None:
    """
    Restore previously stashed remote paths and clean up the temp directory.
    """
    for rel in relative_paths:
        safe_rel = rel.strip().strip("/")
        if not safe_rel:
            continue
        src_path = f"{tmp_dir}/{safe_rel}"
        dest_path = f"{remote_dir.rstrip('/')}/{safe_rel}"
        cmd = (
            "set -euo pipefail; "
            f"if [ -e {src_path} ]; then "
            f"mkdir -p $(dirname {dest_path}); "
            f"cp -a {src_path} {dest_path}; "
            "fi"
        )
        utils.ssh_command(
            host,
            user,
            cmd,
            stream_output=True,
            check=False,
        )

    utils.ssh_command(
        host,
        user,
        f"rm -rf {tmp_dir}",
        stream_output=True,
        check=False,
    )
