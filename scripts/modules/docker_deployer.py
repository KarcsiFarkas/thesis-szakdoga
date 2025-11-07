"""
Docker Compose service deployment.

This module handles the deployment of Docker Compose services with
profile-based configuration.
"""

import time
from typing import List

from . import constants
from . import utils


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
