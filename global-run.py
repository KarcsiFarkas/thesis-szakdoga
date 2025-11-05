#!/usr/bin/env python3
"""
Full-stack orchestrator for Proxmox and Docker/NixOS services.

This is the main entry point for the PaaS deployment orchestration system.
It coordinates VM provisioning, service deployment, and configuration management.
"""

import argparse
import sys
import yaml

from scripts.modules import (
    config_manager,
    proxmox_provisioner,
    docker_deployer,
    nix_deployer,
    traefik_config,
    utils,
    constants
)


def deploy_docker_runtime(tenant_name: str, general_config: dict) -> None:
    """
    Execute Docker-based deployment workflow.

    Args:
        tenant_name: Name of the tenant
        general_config: General tenant configuration
    """
    print("\n--- Step 3: Docker Service Deployment ---")

    # Step 3a: Load Service Definitions
    services_definition = config_manager.load_services_definition()

    # Step 3b: Generate Docker Configuration
    general_conf, selection_conf = config_manager.load_tenant_config(tenant_name)
    config_manager.generate_dotenv(general_conf, selection_conf, services_definition)

    # Step 3c: Deploy Core Services
    docker_deployer.deploy_core_services()

    # Step 3d: Configure Traefik and Dashboard
    print("\n--- Configuring Traefik and Dashboard ---")
    traefik_config.generate_traefik_dynamic_config(general_conf, selection_conf)
    # TODO: Implement generate_homepage_config(general_conf, selection_conf)
    print("🔧 Generating Homepage dashboard configuration... (TODO)")

    traefik_config.restart_traefik()

    print("\n🎉 Deployment process finished! 🎉")
    domain = general_conf.get("tenant_domain", constants.DEFAULT_DOMAIN)
    print("\nAccess services at:")
    print(f"  - Traefik Dashboard: http://localhost:8080 (or https://traefik.{domain} if configured)")
    print(f"  - Homepage: https://homepage.{domain}")
    print(f"  - Vaultwarden: https://vaultwarden.{domain}")


def deploy_nix_runtime(tenant_name: str, vm_to_provision: str, vm_username: str) -> None:
    """
    Execute NixOS-based deployment workflow.

    Args:
        tenant_name: Name of the tenant
        vm_to_provision: Name of the VM to provision
        vm_username: SSH username for the VM
    """
    # Step 3 (Nix): Stage and install flake on the remote NixOS machine
    print("\n--- Step 3: Staging NixOS flake for selected services ---")
    staged_dir = nix_deployer.stage_nix_solution_for_tenant(tenant_name)

    print("\n--- Step 4: NixOS Flake Installation ---")
    nix_deployer.install_nixos_flake_via_ssh(vm_to_provision, vm_username, local_nix_dir=staged_dir)

    print("\n🎉 Nix deployment process finished! Reboot the VM to apply if needed. 🎉")


def main(tenant_name: str) -> None:
    """
    Main execution flow for orchestration.

    Args:
        tenant_name: Name of the tenant to deploy
    """
    print(f"✨ Starting deployment process for tenant: {tenant_name} ✨")

    # Step 1: Validate Configurations
    print("\n--- Step 1: Validating Configurations ---")
    vm_to_provision = config_manager.lint_configurations(tenant_name)

    # Load the tenant general config
    print(f"🔧 Loading tenant config for {tenant_name}...")
    tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant_name
    general_conf_path = tenant_dir / "general.conf.yml"
    with open(general_conf_path, 'r') as f:
        general_config = yaml.safe_load(f) or {}

    deployment_runtime = str(general_config.get("deployment_runtime", "docker")).lower()

    # Determine SSH username
    vm_username = config_manager.get_deployment_username(general_config, vm_to_provision)

    # Step 2: Provision Proxmox VM
    print(f"\n--- Step 2: Provisioning Proxmox VM ({vm_to_provision}) ---")
    proxmox_provisioner.provision_proxmox_vm(vm_to_provision, vm_username)

    # Step 3+: Runtime-specific deployment
    if deployment_runtime == "nix":
        deploy_nix_runtime(tenant_name, vm_to_provision, vm_username)
    else:
        deploy_docker_runtime(tenant_name, general_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Full-stack orchestrator for Proxmox and Docker services."
    )
    parser.add_argument(
        "tenant",
        help="The name of the tenant configuration to use (e.g., 'test')."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug output and real-time subprocess logs."
    )
    args = parser.parse_args()

    # Set global DEBUG flag via context
    utils.DebugContext.set_debug(args.debug)
    if args.debug:
        print("🐞 Debug mode enabled: streaming subprocess output and verbose logs.")

    main(args.tenant)
