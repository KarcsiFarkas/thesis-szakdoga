"""
Deployment Rollback Module

Handles automatic and manual rollback of failed deployments.
Creates snapshots, manages rollback procedures, and ensures safe recovery.
"""

import hashlib
import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import constants, utils
from .deployment_state_manager import DeploymentState, DeploymentStateManager, DeploymentStatus


class RollbackError(Exception):
    """Raised when rollback operations fail."""
    pass


class DeploymentSnapshot:
    """Manages deployment configuration snapshots for rollback."""

    SNAPSHOT_DIR_NAME = "deployment-snapshots"

    def __init__(self, tenant: str, snapshot_dir: Optional[Path] = None):
        """
        Initialize deployment snapshot manager.

        Args:
            tenant: Tenant name
            snapshot_dir: Directory to store snapshots (default: tenant state dir)
        """
        self.tenant = tenant

        if snapshot_dir is None:
            tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant
            self.snapshot_dir = tenant_dir / "state" / self.SNAPSHOT_DIR_NAME
        else:
            self.snapshot_dir = snapshot_dir

        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(
        self,
        deployment_id: str,
        vm_host: str,
        vm_user: str,
        description: Optional[str] = None
    ) -> Path:
        """
        Create snapshot of current deployment configuration.

        Args:
            deployment_id: Unique deployment identifier
            vm_host: VM hostname or IP
            vm_user: SSH username
            description: Optional snapshot description

        Returns:
            Path to snapshot archive

        Raises:
            RollbackError: If snapshot creation fails
        """
        utils.log_info(f"📸 Creating deployment snapshot: {deployment_id}")

        snapshot_name = f"snapshot-{deployment_id}"
        snapshot_path = self.snapshot_dir / f"{snapshot_name}.tar.gz"
        temp_dir = self.snapshot_dir / f"{snapshot_name}-temp"

        try:
            # Create temporary directory for snapshot files
            temp_dir.mkdir(exist_ok=True)

            # Download current configurations from VM
            self._download_configurations(vm_host, vm_user, temp_dir)

            # Create metadata file
            metadata = {
                "deployment_id": deployment_id,
                "tenant": self.tenant,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "vm_host": vm_host,
                "vm_user": vm_user,
                "description": description or f"Snapshot for deployment {deployment_id}"
            }

            metadata_file = temp_dir / "snapshot-metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Create archive
            with tarfile.open(snapshot_path, 'w:gz') as tar:
                tar.add(temp_dir, arcname=snapshot_name)

            utils.log_success(f"✅ Snapshot created: {snapshot_path}")
            utils.log_info(f"   Size: {snapshot_path.stat().st_size / 1024:.2f} KB")

            # Cleanup old snapshots (keep last 5)
            self._cleanup_old_snapshots(keep=5)

            return snapshot_path

        except Exception as e:
            raise RollbackError(f"Failed to create snapshot: {e}") from e

        finally:
            # Cleanup temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _download_configurations(self, vm_host: str, vm_user: str, dest_dir: Path) -> None:
        """
        Download deployment configurations from VM.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
            dest_dir: Destination directory for downloaded files
        """
        utils.log_info("📥 Downloading configuration files from VM...")

        # Files to backup
        remote_files = [
            "~/paas-deployment/docker-compose.yml",
            "~/paas-deployment/.env",
            "~/paas-deployment/configs/",
            "/opt/deployment-state.yml"
        ]

        for remote_file in remote_files:
            # Check if file exists
            check_cmd = f"test -e {remote_file} && echo 'exists' || echo 'missing'"
            result = utils.ssh_command(vm_host, vm_user, check_cmd, check=False)

            if "exists" not in result.stdout:
                utils.log_warn(f"File not found on VM: {remote_file}")
                continue

            # Download file
            local_name = remote_file.replace("~/", "").replace("/", "_")
            local_path = dest_dir / local_name

            try:
                utils.scp_download(
                    vm_host,
                    vm_user,
                    remote_file,
                    str(local_path),
                    recursive=remote_file.endswith("/")
                )
                utils.log_info(f"✅ Downloaded: {remote_file}")

            except Exception as e:
                utils.log_warn(f"Failed to download {remote_file}: {e}")

    def _cleanup_old_snapshots(self, keep: int = 5) -> None:
        """
        Remove old snapshots, keeping only the most recent.

        Args:
            keep: Number of snapshots to keep
        """
        snapshots = sorted(
            self.snapshot_dir.glob("snapshot-*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for snapshot in snapshots[keep:]:
            try:
                snapshot.unlink()
                utils.log_info(f"🗑️  Removed old snapshot: {snapshot.name}")
            except Exception as e:
                utils.log_warn(f"Failed to delete snapshot {snapshot.name}: {e}")

    def list_snapshots(self) -> List[Dict]:
        """
        List available snapshots.

        Returns:
            List of snapshot metadata dictionaries
        """
        snapshots = []

        for snapshot_file in sorted(self.snapshot_dir.glob("snapshot-*.tar.gz"), reverse=True):
            try:
                # Extract metadata from archive
                with tarfile.open(snapshot_file, 'r:gz') as tar:
                    # Find metadata file
                    metadata_files = [m for m in tar.getmembers() if m.name.endswith("snapshot-metadata.json")]

                    if metadata_files:
                        metadata_file = tar.extractfile(metadata_files[0])
                        metadata = json.load(metadata_file)

                        metadata['snapshot_file'] = str(snapshot_file)
                        metadata['size_kb'] = snapshot_file.stat().st_size / 1024

                        snapshots.append(metadata)

            except Exception as e:
                utils.log_warn(f"Failed to read snapshot {snapshot_file.name}: {e}")

        return snapshots

    def restore_snapshot(
        self,
        snapshot_file: Path,
        vm_host: str,
        vm_user: str
    ) -> bool:
        """
        Restore deployment from snapshot.

        Args:
            snapshot_file: Path to snapshot archive
            vm_host: VM hostname or IP
            vm_user: SSH username

        Returns:
            True if restore successful

        Raises:
            RollbackError: If restore fails
        """
        utils.log_info(f"♻️  Restoring from snapshot: {snapshot_file.name}")

        temp_dir = self.snapshot_dir / f"restore-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        try:
            # Extract snapshot
            temp_dir.mkdir(exist_ok=True)

            with tarfile.open(snapshot_file, 'r:gz') as tar:
                tar.extractall(temp_dir)

            # Find extracted directory
            extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise RollbackError("No directory found in snapshot archive")

            restore_dir = extracted_dirs[0]

            # Load metadata
            metadata_file = restore_dir / "snapshot-metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    utils.log_info(f"📋 Snapshot info: {metadata.get('description', 'N/A')}")
                    utils.log_info(f"   Created: {metadata.get('timestamp', 'Unknown')}")

            # Upload configurations to VM
            self._upload_configurations(vm_host, vm_user, restore_dir)

            utils.log_success("✅ Snapshot restored successfully")
            return True

        except Exception as e:
            raise RollbackError(f"Failed to restore snapshot: {e}") from e

        finally:
            # Cleanup temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _upload_configurations(self, vm_host: str, vm_user: str, source_dir: Path) -> None:
        """
        Upload configuration files to VM.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
            source_dir: Source directory with files to upload
        """
        utils.log_info("📤 Uploading configuration files to VM...")

        # Map local files to remote paths
        file_mapping = {
            "paas-deployment_docker-compose.yml": "~/paas-deployment/docker-compose.yml",
            "paas-deployment_.env": "~/paas-deployment/.env",
            "paas-deployment_configs_": "~/paas-deployment/configs/",
            "_opt_deployment-state.yml": "/opt/deployment-state.yml"
        }

        for local_name, remote_path in file_mapping.items():
            local_path = source_dir / local_name

            if not local_path.exists():
                utils.log_warn(f"File not found in snapshot: {local_name}")
                continue

            # Create remote directory if needed
            remote_dir = str(Path(remote_path).parent)
            utils.ssh_command(vm_host, vm_user, f"mkdir -p {remote_dir}", check=False)

            # Upload file
            try:
                utils.scp_upload(
                    vm_host,
                    vm_user,
                    str(local_path),
                    remote_path,
                    recursive=local_path.is_dir()
                )
                utils.log_info(f"✅ Uploaded: {remote_path}")

            except Exception as e:
                utils.log_warn(f"Failed to upload {local_name}: {e}")


class DeploymentRollback:
    """Manages deployment rollback operations."""

    def __init__(self, tenant: str):
        """
        Initialize deployment rollback manager.

        Args:
            tenant: Tenant name
        """
        self.tenant = tenant
        self.state_manager = DeploymentStateManager(tenant)
        self.snapshot_manager = DeploymentSnapshot(tenant)

    def can_rollback(self) -> Tuple[bool, Optional[str]]:
        """
        Check if rollback is possible.

        Returns:
            Tuple of (can_rollback, reason)
        """
        current_state = self.state_manager.load_state()

        if current_state is None:
            return False, "No deployment state found"

        if not current_state.rollback_available:
            return False, "No previous deployment available"

        if current_state.status == DeploymentStatus.ROLLING_BACK:
            return False, "Rollback already in progress"

        if current_state.status == DeploymentStatus.ROLLED_BACK:
            return False, "Already rolled back"

        return True, None

    def rollback_deployment(
        self,
        vm_host: str,
        vm_user: str,
        verify_health: bool = True
    ) -> bool:
        """
        Perform deployment rollback.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
            verify_health: Whether to verify health after rollback

        Returns:
            True if rollback successful

        Raises:
            RollbackError: If rollback fails
        """
        utils.log_info(f"🔄 Starting rollback for tenant: {self.tenant}")

        # Check if rollback is possible
        can_rollback, reason = self.can_rollback()
        if not can_rollback:
            raise RollbackError(f"Rollback not possible: {reason}")

        # Mark rollback started
        self.state_manager.mark_rollback_started()

        try:
            # Get previous state
            previous_state = self.state_manager.get_previous_state()
            if previous_state is None:
                raise RollbackError("Previous deployment state not found")

            utils.log_info(f"📋 Rolling back to: {previous_state.deployment_id}")

            # Find corresponding snapshot
            snapshots = self.snapshot_manager.list_snapshots()
            matching_snapshot = None

            for snapshot in snapshots:
                if snapshot['deployment_id'] == previous_state.deployment_id:
                    matching_snapshot = Path(snapshot['snapshot_file'])
                    break

            if matching_snapshot is None:
                raise RollbackError(f"Snapshot not found for deployment: {previous_state.deployment_id}")

            # Stop current services
            self._stop_services(vm_host, vm_user)

            # Restore snapshot
            self.snapshot_manager.restore_snapshot(matching_snapshot, vm_host, vm_user)

            # Restart services
            self._restart_services(vm_host, vm_user)

            # Verify health if requested
            if verify_health:
                self._verify_rollback_health(vm_host, vm_user)

            # Mark rollback complete
            self.state_manager.mark_rollback_complete()

            utils.log_success(f"✅ Rollback completed successfully")
            utils.log_info(f"   Restored to: {previous_state.deployment_id}")

            return True

        except Exception as e:
            utils.log_error(f"Rollback failed: {e}")
            raise RollbackError(f"Rollback failed: {e}") from e

    def _stop_services(self, vm_host: str, vm_user: str) -> None:
        """
        Stop current services on VM.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
        """
        utils.log_info("⏹️  Stopping current services...")

        cmd = "cd ~/paas-deployment && docker compose down"
        result = utils.ssh_command(vm_host, vm_user, cmd, check=False)

        if result.returncode != 0:
            utils.log_warn(f"Failed to stop services gracefully: {result.stderr}")
            # Force stop if needed
            force_cmd = "cd ~/paas-deployment && docker compose kill"
            utils.ssh_command(vm_host, vm_user, force_cmd, check=False)

        utils.log_info("✅ Services stopped")

    def _restart_services(self, vm_host: str, vm_user: str) -> None:
        """
        Restart services after rollback.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
        """
        utils.log_info("🔄 Restarting services...")

        cmd = "cd ~/paas-deployment && docker compose up -d"
        result = utils.ssh_command(vm_host, vm_user, cmd, stream_output=True, check=False)

        if result.returncode != 0:
            raise RollbackError(f"Failed to restart services: {result.stderr}")

        utils.log_info("✅ Services restarted")

    def _verify_rollback_health(self, vm_host: str, vm_user: str) -> None:
        """
        Verify service health after rollback.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
        """
        utils.log_info("🏥 Verifying service health...")

        # Wait for services to stabilize
        import time
        time.sleep(10)

        cmd = "cd ~/paas-deployment && docker compose ps --format json"
        result = utils.ssh_command(vm_host, vm_user, cmd, check=False)

        if result.returncode == 0:
            try:
                # Parse container statuses
                containers = json.loads(result.stdout) if result.stdout.strip() else []
                healthy = sum(1 for c in containers if 'running' in c.get('State', '').lower())
                total = len(containers)

                utils.log_info(f"📊 Health check: {healthy}/{total} services running")

                if healthy < total:
                    utils.log_warn(f"⚠️  Some services are not healthy after rollback")
            except json.JSONDecodeError:
                utils.log_warn("Could not parse service health status")
        else:
            utils.log_warn("Failed to verify service health")

    def create_pre_deployment_snapshot(
        self,
        deployment_id: str,
        vm_host: str,
        vm_user: str
    ) -> Optional[Path]:
        """
        Create snapshot before deployment for rollback capability.

        Args:
            deployment_id: Unique deployment identifier
            vm_host: VM hostname or IP
            vm_user: SSH username

        Returns:
            Path to snapshot if successful, None otherwise
        """
        try:
            snapshot_path = self.snapshot_manager.create_snapshot(
                deployment_id=deployment_id,
                vm_host=vm_host,
                vm_user=vm_user,
                description=f"Pre-deployment snapshot for {deployment_id}"
            )
            return snapshot_path

        except Exception as e:
            utils.log_error(f"Failed to create pre-deployment snapshot: {e}")
            return None


def perform_rollback(tenant: str, vm_host: str, vm_user: str) -> bool:
    """
    Perform deployment rollback for a tenant.

    Args:
        tenant: Tenant name
        vm_host: VM hostname or IP
        vm_user: SSH username

    Returns:
        True if rollback successful
    """
    rollback = DeploymentRollback(tenant)

    try:
        return rollback.rollback_deployment(vm_host, vm_user)
    except RollbackError as e:
        utils.log_error(f"Rollback failed: {e}")
        return False


def create_deployment_snapshot(
    tenant: str,
    deployment_id: str,
    vm_host: str,
    vm_user: str
) -> Optional[Path]:
    """
    Create deployment snapshot for rollback.

    Args:
        tenant: Tenant name
        deployment_id: Unique deployment identifier
        vm_host: VM hostname or IP
        vm_user: SSH username

    Returns:
        Path to snapshot if successful
    """
    rollback = DeploymentRollback(tenant)
    return rollback.create_pre_deployment_snapshot(deployment_id, vm_host, vm_user)
