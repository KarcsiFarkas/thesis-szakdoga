#!/usr/bin/env python3
"""
Full-stack orchestrator for Proxmox and Docker/NixOS services.

This is the main entry point for the PaaS deployment orchestration system.
It coordinates VM provisioning, service deployment, and configuration management.
"""

import argparse
import json
import os
import platform
import shutil
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from scripts.modules import (
    chezmoi_deployer,
    config_manager,
    credential_manager,
    proxmox_provisioner,
    docker_deployer,
    nix_deployer,
    nixos_anywhere_deployer,
    traefik_config,
    utils,
    constants
)


class DeploymentMetrics:
    def __init__(self, tenant: str, enabled: bool, log_path: str | None = None):
        self.enabled = enabled
        self.tenant = tenant
        self.start_time = time.perf_counter()
        self.data: dict[str, object] = {
            "tenant": tenant,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "environment": {
                "host": socket.gethostname(),
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "cpu_count": os.cpu_count(),
            },
            "steps": [],
            "disk_snapshots": [],
        }
        tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant
        self.metrics_dir = tenant_dir / "metrics"
        if self.enabled:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._step_starts: dict[str, float] = {}
        self._log_path: Path | None = Path(log_path) if log_path else None

    def add_info(self, key: str, value: object) -> None:
        if not self.enabled:
            return
        self.data.setdefault("metadata", {})[key] = value

    def disk_snapshot(self, label: str, path: Path | None = None) -> None:
        if not self.enabled:
            return
        target = path or constants.ROOT_DIR
        try:
            usage = shutil.disk_usage(target)
        except FileNotFoundError:
            return
        snapshot = {
            "label": label,
            "path": str(target),
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round((usage.total - usage.free) / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
        }
        self.data["disk_snapshots"].append(snapshot)

    def step_start(self, name: str) -> None:
        if not self.enabled:
            return
        self._step_starts[name] = time.perf_counter()

    def step_end(self, name: str, status: str = "completed", extra: dict | None = None) -> None:
        if not self.enabled:
            return
        started = self._step_starts.pop(name, None)
        duration = (time.perf_counter() - started) if started else None
        entry = {
            "name": name,
            "status": status,
        }
        if duration is not None:
            entry["duration_seconds"] = round(duration, 2)
        if extra:
            entry["details"] = extra
        self.data["steps"].append(entry)

    def step_skip(self, name: str, reason: str = "skipped") -> None:
        if not self.enabled:
            return
        self.data["steps"].append({"name": name, "status": reason})

    def finish(self, *, error: Exception | None = None) -> None:
        if not self.enabled:
            return
        finished_at = datetime.utcnow().isoformat() + "Z"
        duration = time.perf_counter() - self.start_time
        self.data["finished_at"] = finished_at
        self.data["duration_seconds"] = round(duration, 2)
        self.data["status"] = "failed" if error else "completed"
        if error:
            self.data["error"] = str(error)

        if not self._log_path:
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            self._log_path = self.metrics_dir / f"metrics-{timestamp}.json"

        # Ensure the parent directory exists
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._log_path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2)
        
        log_file_path = self._log_path.resolve()
        utils.log_info(f"📊 Metrics saved to {log_file_path}")
        print(f"Log file saved to: {log_file_path}")


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


def deploy_nix_runtime(
    tenant_name: str,
    general_config: dict,
    vm_to_provision: str,
    vm_username: str,
) -> None:
    """
    Execute NixOS-based deployment workflow.

    Args:
        tenant_name: Name of the tenant
        general_config: Tenant general configuration
        vm_to_provision: Name of the VM to provision
        vm_username: SSH username for the VM
    """
    section("Step 3: NixOS Deployment (nixos-anywhere)")
    try:
        nixos_anywhere_deployer.deploy_with_nixos_anywhere(
            tenant_name,
            vm_to_provision,
            vm_username,
            general_config,
        )
        section("Nix Deployment")
        utils.log_success("Nix deployment process finished via nixos-anywhere!")
        return
    except nixos_anywhere_deployer.NixosAnywhereDeploymentError as exc:
        utils.log_warn(f"nixos-anywhere deployment failed: {exc}")
        utils.log_warn("Falling back to legacy nix flake installation...")

    # Fallback: Stage and install the legacy flake on the remote NixOS machine
    section("Fallback: Staging NixOS flake for selected services")
    staged_dir = nix_deployer.stage_nix_solution_for_tenant(tenant_name)

    section("Fallback: NixOS flake installation")
    nix_deployer.install_nixos_flake_via_ssh(vm_to_provision, vm_username, local_nix_dir=staged_dir)

    section("Nix Deployment")
    utils.log_success("Nix deployment process finished via nix flake fallback. Reboot the VM to apply if needed.")


def main(tenant_name: str, start_from_step: int = 1, *, metrics_enabled: bool = False, skip_credentials: bool = False, log_file: str | None = None) -> None:
    """
    Main execution flow for orchestration.

    Args:
        tenant_name: Name of the tenant to deploy
        start_from_step: Step number to start from (1=validate, 2=provision, 3=credentials, 4=deploy)
        skip_credentials: Skip credential generation step
        log_file: Path to save the metrics log file.
    """
    utils.log_info(f"✨ Starting deployment process for tenant: {tenant_name} ✨")
    key_path = utils.ensure_tenant_ssh_identity(tenant_name)
    utils.set_default_ssh_identity(key_path)
    metrics = DeploymentMetrics(tenant_name, metrics_enabled, log_path=log_file)
    metrics.add_info("start_from_step", start_from_step)

    if start_from_step > 1:
        utils.log_warn(f"⚡ Starting from step {start_from_step} (skipping earlier steps)")

    metrics.disk_snapshot("start-root", constants.ROOT_DIR)
    metrics.disk_snapshot("start-docker", constants.DOCKER_LEGACY_DIR)

    error: Exception | None = None
    try:
        # Step 1: Validate Configurations
        if start_from_step <= 1:
            section("Step 1: Validating Configurations")
            metrics.step_start("validate_configurations")
            try:
                vm_to_provision = config_manager.lint_configurations(tenant_name)
                metrics.step_end("validate_configurations", extra={"vm": vm_to_provision})
            except Exception:
                metrics.step_end("validate_configurations", status="failed")
                raise
        else:
            section("Step 1: Validating Configurations (SKIPPED)")
            metrics.step_skip("validate_configurations")
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

        deployment_runtime_raw = str(general_config.get("deployment_runtime", "docker"))
        deployment_runtime = deployment_runtime_raw.lower()
        deployment_runtime_normalized = deployment_runtime.replace("_", "-")
        metrics.add_info("deployment_runtime", deployment_runtime)
        metrics.add_info("tenant_domain", general_config.get("tenant_domain"))
        metrics.add_info("vm_target", vm_to_provision)

        # Determine SSH username
        vm_username = config_manager.get_deployment_username(general_config, vm_to_provision)

        # Step 2: Provision Proxmox VM
        if start_from_step <= 2:
            section(f"Step 2: Provisioning Proxmox VM ({vm_to_provision})")
            metrics.step_start("provision_vm")
            try:
                proxmox_provisioner.provision_proxmox_vm(vm_to_provision, vm_username)
                metrics.step_end("provision_vm", extra={"vm": vm_to_provision})
            except Exception:
                metrics.step_end("provision_vm", status="failed")
                raise
        else:
            section(f"Step 2: Provisioning Proxmox VM ({vm_to_provision}) (SKIPPED)")
            metrics.step_skip("provision_vm")

        # Step 3: Generate Credentials
        temp_auth_dir = None
        if not skip_credentials and start_from_step <= 3:
            section("Step 3: Generating Service Credentials")
            metrics.step_start("generate_credentials")
            try:
                password_mode = general_config.get("password_mode", "global")
                global_password = os.environ.get("GLOBAL_PASSWORD")

                # Validate global password if needed
                if password_mode != "generate" and not global_password:
                    utils.log_warn("⚠️  password_mode is not 'generate' but GLOBAL_PASSWORD not set")
                    utils.log_warn("⚠️  Skipping credential generation. Set GLOBAL_PASSWORD or change password_mode to 'generate'")
                    metrics.step_skip("generate_credentials", reason="no_global_password")
                else:
                    temp_auth_dir = credential_manager.generate_credentials(
                        tenant_name,
                        global_password=global_password
                    )
                    metrics.step_end("generate_credentials", extra={"credentials_dir": str(temp_auth_dir)})

                    utils.log_info("")
                    utils.log_info("📋 Credential files generated:")
                    utils.log_info(f"   Location: {temp_auth_dir}")
                    utils.log_info("   - credentials.env (service credentials)")
                    utils.log_info("   - db-credentials.env (database credentials)")
                    utils.log_info("   - bitwarden-import.json (for bw CLI import)")
                    utils.log_info("   - bitwarden-import.csv (for web UI import)")
                    utils.log_info("")
                    utils.log_warn("⚠️  Remember to import to Bitwarden after deployment!")
                    utils.log_info(f"📖 See {temp_auth_dir}/README.md for import instructions")
                    utils.log_info("")

            except credential_manager.CredentialManagerError as e:
                utils.log_error(f"Credential generation failed: {e}")
                metrics.step_end("generate_credentials", status="failed")
                utils.log_warn("Continuing without credential generation...")
            except Exception:
                metrics.step_end("generate_credentials", status="failed")
                raise
        else:
            if skip_credentials:
                section("Step 3: Generating Service Credentials (SKIPPED - disabled)")
            else:
                section("Step 3: Generating Service Credentials (SKIPPED)")
            metrics.step_skip("generate_credentials")

        # Step 4+: Runtime-specific deployment
        if start_from_step <= 4:
            metrics.step_start("deploy_runtime")
            try:
                if deployment_runtime_normalized in {"nix", "nixos", "nixos-anywhere", "proxmox"}:
                    deploy_nix_runtime(tenant_name, general_config, vm_to_provision, vm_username)
                else:
                    deploy_docker_runtime(tenant_name, general_config, vm_to_provision, vm_username)
                metrics.step_end("deploy_runtime", extra={"runtime": deployment_runtime})
            except Exception:
                metrics.step_end("deploy_runtime", status="failed")
                raise
        else:
            section("Step 4: Service Deployment (SKIPPED)")
            metrics.step_skip("deploy_runtime")

    except Exception as exc:
        error = exc
        raise
    finally:
        metrics.disk_snapshot("end-root", constants.ROOT_DIR)
        metrics.disk_snapshot("end-docker", constants.DOCKER_LEGACY_DIR)
        metrics.finish(error=error)


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
        "--metrics",
        action="store_true",
        help="Record deployment metrics (overrides METRIC env var)."
    )
    parser.add_argument(
        "--start-from-step",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help="Step to start deployment from: 1=Validate Config, 2=Provision VM, 3=Generate Credentials, 4=Deploy Services (default: 1)"
    )
    parser.add_argument(
        "--skip-credentials",
        action="store_true",
        help="Skip credential generation step (use existing or manual credentials)"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Save the metrics log to a specific file path. If not set, a timestamped file is created in the tenant's metrics directory."
    )
    args = parser.parse_args()

    # Set global DEBUG flag via context
    utils.DebugContext.set_debug(args.debug)
    if args.debug:
        utils.log_warn("🐞 Debug mode enabled: streaming subprocess output and verbose logs.")

    if args.no_chezmoi:
        utils.log_warn("⚠️ Chezmoi disabled - using legacy deployment method")

    env_metric = os.environ.get("METRIC", "")
    metrics_enabled = args.metrics or env_metric.lower() in {"1", "true", "yes", "on"}

    main(
        args.tenant,
        start_from_step=args.start_from_step,
        metrics_enabled=metrics_enabled,
        skip_credentials=args.skip_credentials,
        log_file=args.log_file
    )
