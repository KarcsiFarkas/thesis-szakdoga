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
    chezmoi_deployer,
    config_manager,
    proxmox_provisioner,
    docker_deployer,
    nix_deployer,
    traefik_config,
    utils,
    constants
)

def section(title: str) -> None:
    print()
    utils.log_info(f"--- {title} ---")

def deploy_docker_runtime(
    tenant_name: str,
    general_config: dict,
    vm_to_provision: str,
    vm_username: str,
    use_chezmoi: bool = True
) -> None:
    """
    Execute Docker-based deployment workflow.

    Args:
        tenant_name: Name of the tenant
        general_config: General tenant configuration
        vm_to_provision: Name of the VM to provision
        vm_username: SSH username for the VM
        use_chezmoi: Whether to use Chezmoi for deployment (default: True)
    """
    section("Step 3: Docker Service Deployment")

    # Load tenant configuration
    general_conf, selection_conf = config_manager.load_tenant_config(tenant_name)

    host_or_ip, _ = utils.get_vm_connection_info(vm_to_provision)

    if use_chezmoi:
        # Step 3a: Deploy via Chezmoi (recommended)
        section("Deploying via Chezmoi Configuration Management")
        try:
            chezmoi_deployer.deploy_via_ssh(
                vm_to_provision,
                vm_username,
                tenant_name,
                general_conf,
                selection_conf
            )

            # Verify deployment
            chezmoi_deployer.verify_deployment(
                vm_to_provision,
                vm_username,
                "docker"
            )

        except chezmoi_deployer.ChezmoiDeploymentError as e:
            utils.log_error(f"Chezmoi deployment failed: {e}")
            utils.log_warn("Falling back to legacy deployment method...")
            use_chezmoi = False

    if not use_chezmoi:
        # Step 3b: Legacy deployment method
        section("Using Legacy Deployment Method")

        # Load Service Definitions
        services_definition = config_manager.load_services_definition()

        # Generate Docker Configuration
        legacy_compose_dir = constants.DOCKER_LEGACY_DIR
        config_manager.generate_dotenv(
            general_conf,
            selection_conf,
            services_definition,
            target_dir=legacy_compose_dir,
        )
        section("Configuring Traefik and Dashboard")
        traefik_config.generate_traefik_dynamic_config(
            general_conf,
            selection_conf,
            output_dir=constants.LEGACY_TRAEFIK_DYNAMIC_DIR,
        )
        utils.log_info("Generating Homepage dashboard configuration... (TODO)")

        # Deploy Core Services remotely
        docker_deployer.deploy_core_services_remote(
            host_or_ip,
            vm_username,
            local_compose_dir=legacy_compose_dir,
            preserve_paths=["configs/homepage"],
            restart_services=["homepage"],
        )
        traefik_config.restart_traefik(host=host_or_ip, user=vm_username)

    section("Deployment Summary")
    utils.log_success("Deployment process finished!")
    domain = general_conf.get("tenant_domain", constants.DEFAULT_DOMAIN)
    service_domains = general_conf.get("service_domains", {}) or {}
    def host_for(service: str, default: str) -> str:
        return service_domains.get(service, default)

    utils.log_info("Access services at:")
    utils.log_info(
        f"  • Traefik Dashboard: https://{host_for('traefik', f'traefik.{domain}')}"
    )
    utils.log_info(
        f"  • Homepage: https://{host_for('homepage', domain)}"
    )
    utils.log_info(
        f"  • Vaultwarden: https://{host_for('vaultwarden', f'vaultwarden.{domain}')}"
    )


def deploy_nix_runtime(tenant_name: str, vm_to_provision: str, vm_username: str) -> None:
    """
    Execute NixOS-based deployment workflow.

    Args:
        tenant_name: Name of the tenant
        vm_to_provision: Name of the VM to provision
        vm_username: SSH username for the VM
    """
    # Step 3 (Nix): Stage and install flake on the remote NixOS machine
    section("Step 3: Staging NixOS flake for selected services")
    staged_dir = nix_deployer.stage_nix_solution_for_tenant(tenant_name)

    section("Step 4: NixOS Flake Installation")
    nix_deployer.install_nixos_flake_via_ssh(vm_to_provision, vm_username, local_nix_dir=staged_dir)

    section("Nix Deployment")
    utils.log_success("Nix deployment process finished! Reboot the VM to apply if needed.")


def main(tenant_name: str, start_from_step: int = 1) -> None:
    """
    Main execution flow for orchestration.

    Args:
        tenant_name: Name of the tenant to deploy
        start_from_step: Step number to start from (1=validate, 2=provision, 3=deploy)
    """
    utils.log_info(f"✨ Starting deployment process for tenant: {tenant_name} ✨")
    key_path = utils.ensure_tenant_ssh_identity(tenant_name)
    utils.set_default_ssh_identity(key_path)

    if start_from_step > 1:
        utils.log_warn(f"⚡ Starting from step {start_from_step} (skipping earlier steps)")

    # Step 1: Validate Configurations
    if start_from_step <= 1:
        section("Step 1: Validating Configurations")
        vm_to_provision = config_manager.lint_configurations(tenant_name)
    else:
        section("Step 1: Validating Configurations (SKIPPED)")
        # Still need to determine VM name even if skipping
        tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant_name
        general_conf_path = tenant_dir / "general.conf.yml"
        with open(general_conf_path, 'r') as f:
            general_config = yaml.safe_load(f) or {}
        vm_to_provision = (
            general_config.get("deployment_target")
            or general_config.get("vm_hostname")
            or f"{tenant_name}-vm"
        )

    # Load the tenant general config
    utils.log_info(f"🔧 Loading tenant config for {tenant_name}...")
    tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant_name
    general_conf_path = tenant_dir / "general.conf.yml"
    with open(general_conf_path, 'r') as f:
        general_config = yaml.safe_load(f) or {}

    deployment_runtime = str(general_config.get("deployment_runtime", "docker")).lower()

    # Determine SSH username
    vm_username = config_manager.get_deployment_username(general_config, vm_to_provision)

    # Step 2: Provision Proxmox VM
    if start_from_step <= 2:
        section(f"Step 2: Provisioning Proxmox VM ({vm_to_provision})")
        proxmox_provisioner.provision_proxmox_vm(vm_to_provision, vm_username)
    else:
        section(f"Step 2: Provisioning Proxmox VM ({vm_to_provision}) (SKIPPED)")

    # Step 3+: Runtime-specific deployment
    if start_from_step <= 3:
        if deployment_runtime == "nix":
            deploy_nix_runtime(tenant_name, vm_to_provision, vm_username)
        else:
            deploy_docker_runtime(tenant_name, general_config, vm_to_provision, vm_username)
    else:
        section("Step 3: Service Deployment (SKIPPED)")


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
    parser.add_argument(
        "--no-chezmoi",
        action="store_true",
        help="Disable Chezmoi and use legacy deployment method."
    )
    parser.add_argument(
        "--start-from-step",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Step to start deployment from: 1=Validate Config, 2=Provision VM, 3=Deploy Services (default: 1)"
    )
    args = parser.parse_args()

    # Set global DEBUG flag via context
    utils.DebugContext.set_debug(args.debug)
    if args.debug:
        utils.log_warn("🐞 Debug mode enabled: streaming subprocess output and verbose logs.")

    if args.no_chezmoi:
        utils.log_warn("⚠️ Chezmoi disabled - using legacy deployment method")

    main(args.tenant, start_from_step=args.start_from_step)
