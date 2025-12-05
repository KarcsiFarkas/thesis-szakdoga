"""
Chezmoi deployment module for configuration management.

This module handles post-Ansible deployment using Chezmoi to manage
Docker Compose configurations, .env files, and service-specific configurations.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from . import constants, utils


class ChezmoiDeploymentError(Exception):
    """Raised when Chezmoi deployment fails."""
    pass


def check_chezmoi_installed() -> bool:
    """
    Check if Chezmoi is installed on the system.

    Returns:
        True if Chezmoi is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["chezmoi", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_chezmoi() -> bool:
    """
    Install Chezmoi if not already installed.

    Returns:
        True if installation successful, False otherwise
    """
    print("🔧 Installing Chezmoi...")

    try:
        # Try package manager first
        if shutil.which("apt-get"):
            subprocess.run(
                ["sudo", "apt-get", "update"],
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", "chezmoi"],
                check=True,
                capture_output=True
            )
        elif shutil.which("pacman"):
            subprocess.run(
                ["sudo", "pacman", "-S", "--noconfirm", "chezmoi"],
                check=True,
                capture_output=True
            )
        else:
            # Use binary install method
            install_script = subprocess.run(
                ["curl", "-fsLS", "get.chezmoi.io"],
                capture_output=True,
                text=True,
                check=True
            ).stdout

            subprocess.run(
                ["sh", "-c", install_script, "--", "-b", f"{Path.home()}/.local/bin"],
                check=True
            )

        print("✅ Chezmoi installed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Chezmoi: {e}")
        return False


def prepare_tenant_configuration(
    tenant_name: str,
    general_config: Dict[str, Any],
    selection_config: Dict[str, Any]
) -> Path:
    """
    Prepare tenant configuration in a temporary directory for Chezmoi deployment.

    Args:
        tenant_name: Name of the tenant
        general_config: General tenant configuration
        selection_config: Service selection configuration

    Returns:
        Path to temporary directory containing tenant configuration
    """
    print(f"🔧 Preparing Chezmoi configuration for tenant: {tenant_name}")

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"tenant-{tenant_name}-"))

    try:
        # Write general configuration
        general_file = temp_dir / "general.conf.yml"
        with open(general_file, 'w') as f:
            yaml.dump(general_config, f, default_flow_style=False)

        # Write selection configuration
        selection_file = temp_dir / "selection.yml"
        with open(selection_file, 'w') as f:
            yaml.dump(selection_config, f, default_flow_style=False)

        print(f"✅ Configuration prepared in: {temp_dir}")
        return temp_dir

    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ChezmoiDeploymentError(f"Failed to prepare configuration: {e}")


def deploy_via_ssh(
    vm_to_provision: str,
    vm_username: str,
    tenant_name: str,
    general_config: Dict[str, Any],
    selection_config: Dict[str, Any]
) -> None:
    """
    Deploy Chezmoi configuration to remote VM via SSH.

    Args:
        vm_to_provision: Name of the VM to deploy to
        vm_username: SSH username for the VM
        tenant_name: Name of the tenant
        general_config: General tenant configuration
        selection_config: Service selection configuration

    Raises:
        ChezmoiDeploymentError: If deployment fails
    """
    print(f"\n🚀 Starting Chezmoi deployment to VM: {vm_to_provision}")

    # Get VM connection info
    host_or_ip, vm_cfg = utils.get_vm_connection_info(vm_to_provision)
    deployment_runtime = general_config.get("deployment_runtime", "docker")
    tenant_domain = general_config.get("tenant_domain", constants.DEFAULT_DOMAIN)
    timezone = general_config.get("timezone", constants.DEFAULT_TIMEZONE)

    # Prepare local configuration
    config_dir = prepare_tenant_configuration(tenant_name, general_config, selection_config)

    try:
        # Copy Chezmoi source directory to VM
        print("📦 Uploading Chezmoi source files to VM...")
        chezmoi_source = constants.ROOT_DIR / "ms-chezmoi"

        remote_temp_dir = f"/tmp/chezmoi-{tenant_name}"

        # Create remote directory
        utils.ssh_command(
            host_or_ip,
            vm_username,
            f"mkdir -p {remote_temp_dir}"
        )

        # Upload Chezmoi source
        utils.scp_upload(
            host_or_ip,
            vm_username,
            str(chezmoi_source),
            f"{remote_temp_dir}/source",
            recursive=True
        )

        # Upload tenant configuration
        utils.scp_upload(
            host_or_ip,
            vm_username,
            str(config_dir),
            f"{remote_temp_dir}/tenant-config",
            recursive=True
        )

        # Upload generated credentials if they exist
        temp_auth_dir = constants.MS_CONFIG_DIR / "tenants" / tenant_name / "temp-auth"
        if temp_auth_dir.exists():
            print("📦 Uploading generated credentials to VM...")
            utils.scp_upload(
                host_or_ip,
                vm_username,
                str(temp_auth_dir),
                f"{remote_temp_dir}/credentials",
                recursive=True
            )
            print("✅ Credentials uploaded successfully")
        else:
            print("⚠️  No credentials found in temp-auth, deployment will use defaults")

        print("✅ Files uploaded successfully")

        # Make deployment script executable
        print("🔧 Setting up deployment script...")
        utils.ssh_command(
            host_or_ip,
            vm_username,
            f"chmod +x {remote_temp_dir}/source/scripts/post-ansible-deploy.sh"
        )

        # Run post-Ansible deployment script
        print("🚀 Running post-Ansible deployment script...")

        deployment_cmd = (
            f"cd {remote_temp_dir}/source && "
            f"TENANT_NAME={tenant_name} "
            f"DEPLOYMENT_RUNTIME={deployment_runtime} "
            f"TENANT_DOMAIN={tenant_domain} "
            f"TIMEZONE={timezone} "
            f"./scripts/post-ansible-deploy.sh "
            f"{tenant_name} {deployment_runtime} {vm_username} "
            f"{tenant_domain} {timezone}"
        )

        result = utils.ssh_command(
            host_or_ip,
            vm_username,
            deployment_cmd,
            stream_output=True
        )

        if result.returncode != 0:
            raise ChezmoiDeploymentError(
                f"Post-Ansible deployment script failed with exit code: {result.returncode}"
            )

        print("✅ Chezmoi deployment completed successfully")

        # Display access information
        print("\n🎉 Deployment Summary:")
        print(f"  Tenant: {tenant_name}")
        print(f"  Domain: {tenant_domain}")
        print(f"  Runtime: {deployment_runtime}")

        if deployment_runtime == "docker":
            print("\n📍 Service URLs:")
            print(f"  Dashboard: https://{tenant_domain}")
            print(f"  Traefik: https://traefik.{tenant_domain}")

            # Show enabled services
            enabled_services = [
                svc_id for svc_id, svc_config in selection_config.get("services", {}).items()
                if svc_config.get("enabled", False)
            ]

            if enabled_services:
                print("\n📦 Enabled Services:")
                for service_id in enabled_services:
                    print(f"  - {service_id}: https://{service_id}.{tenant_domain}")

    except Exception as e:
        raise ChezmoiDeploymentError(f"Chezmoi deployment failed: {e}")

    finally:
        # Clean up local temporary directory
        shutil.rmtree(config_dir, ignore_errors=True)

        # Optionally clean up remote temporary directory
        try:
            utils.ssh_command(
                host_or_ip,
                vm_username,
                f"rm -rf {remote_temp_dir}",
                check=False
            )
        except Exception:
            pass  # Ignore cleanup errors


def verify_deployment(
    vm_to_provision: str,
    vm_username: str,
    deployment_runtime: str
) -> bool:
    """
    Verify that Chezmoi deployment was successful.

    Args:
        vm_to_provision: Name of the VM
        vm_username: SSH username for the VM
        deployment_runtime: Type of deployment (docker/nix)

    Returns:
        True if verification successful, False otherwise
    """
    print("\n🔍 Verifying Chezmoi deployment...")

    host_or_ip, _ = utils.get_vm_connection_info(vm_to_provision)

    try:
        # Check if Chezmoi is installed
        result = utils.ssh_command(
            host_or_ip,
            vm_username,
            "chezmoi --version",
            check=False
        )

        if result.returncode != 0:
            print("❌ Chezmoi not found on remote system")
            return False

        print("✅ Chezmoi is installed")

        # Check if configuration was applied
        result = utils.ssh_command(
            host_or_ip,
            vm_username,
            "chezmoi managed",
            check=False
        )

        if result.returncode != 0:
            print("❌ Chezmoi configuration not applied")
            return False

        managed_files = result.stdout.strip().split('\n')
        print(f"✅ Chezmoi managing {len(managed_files)} files")

        # Runtime-specific verification
        if deployment_runtime == "docker":
            # Check if docker-compose.yml exists
            result = utils.ssh_command(
                host_or_ip,
                vm_username,
                "test -f ~/paas-deployment/docker-compose.yml",
                check=False
            )

            if result.returncode != 0:
                print("❌ docker-compose.yml not found")
                return False

            print("✅ docker-compose.yml deployed")

            # Check if Docker services are running
            result = utils.ssh_command(
                host_or_ip,
                vm_username,
                "cd ~/paas-deployment && docker compose ps --format json",
                check=False
            )

            if result.returncode == 0:
                print("✅ Docker services verified")
            else:
                print("⚠️ Could not verify Docker services")

        print("✅ Deployment verification completed")
        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def update_configuration(
    vm_to_provision: str,
    vm_username: str
) -> bool:
    """
    Update Chezmoi configuration on remote VM.

    Args:
        vm_to_provision: Name of the VM
        vm_username: SSH username for the VM

    Returns:
        True if update successful, False otherwise
    """
    print(f"\n🔄 Updating Chezmoi configuration on VM: {vm_to_provision}")

    host_or_ip, _ = utils.get_vm_connection_info(vm_to_provision)

    try:
        # Run chezmoi update
        result = utils.ssh_command(
            host_or_ip,
            vm_username,
            "chezmoi update --verbose",
            stream_output=True,
            check=False
        )

        if result.returncode != 0:
            print("❌ Chezmoi update failed")
            return False

        print("✅ Configuration updated successfully")
        return True

    except Exception as e:
        print(f"❌ Update failed: {e}")
        return False
