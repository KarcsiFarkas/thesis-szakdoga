"""
Traefik dynamic configuration generation and management.

This module handles:
- Generation of Traefik dynamic configuration files
- Service routing configuration
- Traefik container restart for config reload
"""

import time
import yaml
from pathlib import Path
from typing import Dict, Any

from . import constants
from . import utils


def generate_traefik_dynamic_config(
    general_config: Dict[str, Any],
    selection_config: Dict[str, Any]
) -> Path:
    """
    Generate the dynamic configuration file for Traefik.

    Creates routing rules and service definitions for all enabled services
    based on tenant configuration.

    Args:
        general_config: General tenant configuration
        selection_config: Service selection configuration

    Returns:
        Path to the generated Traefik config file

    Raises:
        SystemExit: If config file cannot be written
    """
    print("🔧 Generating Traefik dynamic configuration...")
    domain = general_config.get("tenant_domain", constants.DEFAULT_DOMAIN)
    traefik_dynamic_dir = constants.TRAEFIK_DYNAMIC_DIR
    traefik_dynamic_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    config_path = constants.TRAEFIK_DYNAMIC_CONFIG_FILE

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
            service_port = constants.SERVICE_PORT_MAPPINGS.get(svc_id, "80")

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
        import sys
        sys.exit(1)


def restart_traefik() -> None:
    """
    Restart the Traefik container to pick up new dynamic config.

    Uses 'docker restart' for a single service rather than compose down/up.
    """
    print(f"🔄 Restarting Traefik to apply configuration...")
    # Using 'docker restart' is simpler than compose down/up for a single service
    utils.run_command(
        ["docker", "restart", "traefik"],
        cwd=constants.DOCKER_COMPOSE_DIR,
        check=False  # check=False in case it wasn't running
    )
    time.sleep(5)  # Give it a moment to restart
    print(f"✅ Traefik restarted.")
