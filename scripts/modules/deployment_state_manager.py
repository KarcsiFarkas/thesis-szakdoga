"""
Deployment State Management Module

Manages deployment state tracking, idempotent deployments, and state transitions.
Ensures deployments can be resumed, updated, and rolled back safely.
"""

import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from . import constants, utils


class DeploymentStatus(str, Enum):
    """Deployment status states."""
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    RUNNING = "running"
    UPDATING = "updating"
    DEGRADED = "degraded"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class ServiceStatus(str, Enum):
    """Service health status."""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class ServiceState:
    """State of a deployed service."""
    name: str
    status: ServiceStatus
    version: Optional[str] = None
    image: Optional[str] = None
    ports: List[int] = field(default_factory=list)
    last_updated: Optional[str] = None
    health_check_failures: int = 0
    environment_hash: Optional[str] = None  # Hash of .env file for change detection

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ServiceState':
        """Create from dictionary."""
        # Handle enum conversion
        if isinstance(data.get('status'), str):
            data['status'] = ServiceStatus(data['status'])
        return cls(**data)


@dataclass
class DeploymentState:
    """Complete deployment state."""
    deployment_id: str
    tenant: str
    status: DeploymentStatus
    runtime: str  # docker or nix
    domain: str
    started_at: str
    updated_at: str
    vm_host: str
    vm_user: str
    services: Dict[str, ServiceState] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    previous_deployment_id: Optional[str] = None
    rollback_available: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert enums to strings
        data['status'] = self.status.value
        data['services'] = {
            name: service.to_dict()
            for name, service in self.services.items()
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'DeploymentState':
        """Create from dictionary."""
        # Handle enum conversion
        if isinstance(data.get('status'), str):
            data['status'] = DeploymentStatus(data['status'])

        # Handle services conversion
        if 'services' in data:
            data['services'] = {
                name: ServiceState.from_dict(svc_data)
                for name, svc_data in data['services'].items()
            }

        return cls(**data)


class DeploymentStateManager:
    """Manages deployment state and enables idempotent operations."""

    STATE_FILE_NAME = "deployment-state.json"
    STATE_BACKUP_DIR = "deployment-state-backups"

    def __init__(self, tenant: str, state_dir: Optional[Path] = None):
        """
        Initialize deployment state manager.

        Args:
            tenant: Tenant name
            state_dir: Directory to store state files (default: tenant metrics dir)
        """
        self.tenant = tenant

        if state_dir is None:
            tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant
            self.state_dir = tenant_dir / "state"
        else:
            self.state_dir = state_dir

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / self.STATE_FILE_NAME
        self.backup_dir = self.state_dir / self.STATE_BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)

        self.current_state: Optional[DeploymentState] = None

    def load_state(self) -> Optional[DeploymentState]:
        """
        Load current deployment state.

        Returns:
            DeploymentState if exists, None otherwise
        """
        if not self.state_file.exists():
            utils.log_info("No existing deployment state found")
            return None

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            self.current_state = DeploymentState.from_dict(data)
            utils.log_info(f"📋 Loaded deployment state: {self.current_state.deployment_id}")
            utils.log_info(f"   Status: {self.current_state.status.value}")
            utils.log_info(f"   Services: {len(self.current_state.services)}")

            return self.current_state

        except Exception as e:
            utils.log_error(f"Failed to load deployment state: {e}")
            return None

    def save_state(self, state: DeploymentState, create_backup: bool = True) -> None:
        """
        Save deployment state.

        Args:
            state: DeploymentState to save
            create_backup: Whether to create backup of previous state
        """
        # Backup existing state
        if create_backup and self.state_file.exists():
            self._backup_current_state()

        # Update timestamp
        state.updated_at = datetime.utcnow().isoformat() + "Z"

        # Save state
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)

            self.current_state = state
            utils.log_info(f"💾 Deployment state saved: {state.deployment_id}")

        except Exception as e:
            utils.log_error(f"Failed to save deployment state: {e}")
            raise

    def _backup_current_state(self) -> None:
        """Backup current state file."""
        if not self.state_file.exists():
            return

        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            backup_file = self.backup_dir / f"state-{timestamp}.json"

            shutil.copy2(self.state_file, backup_file)
            utils.log_info(f"📦 Previous state backed up to: {backup_file}")

            # Keep only last 10 backups
            self._cleanup_old_backups(keep=10)

        except Exception as e:
            utils.log_warn(f"Failed to backup state: {e}")

    def _cleanup_old_backups(self, keep: int = 10) -> None:
        """Clean up old backup files, keeping only the most recent."""
        backups = sorted(self.backup_dir.glob("state-*.json"), reverse=True)

        for backup in backups[keep:]:
            try:
                backup.unlink()
            except Exception as e:
                utils.log_warn(f"Failed to delete old backup {backup}: {e}")

    def create_new_deployment(
        self,
        runtime: str,
        domain: str,
        vm_host: str,
        vm_user: str,
        metadata: Optional[Dict] = None
    ) -> DeploymentState:
        """
        Create a new deployment state.

        Args:
            runtime: Deployment runtime (docker/nix)
            domain: Tenant domain
            vm_host: VM hostname or IP
            vm_user: SSH username
            metadata: Additional metadata

        Returns:
            New DeploymentState
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        deployment_id = f"deploy-{timestamp}"

        # Check for existing deployment
        previous_state = self.load_state()
        previous_deployment_id = previous_state.deployment_id if previous_state else None

        state = DeploymentState(
            deployment_id=deployment_id,
            tenant=self.tenant,
            status=DeploymentStatus.INITIALIZING,
            runtime=runtime,
            domain=domain,
            started_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
            vm_host=vm_host,
            vm_user=vm_user,
            previous_deployment_id=previous_deployment_id,
            rollback_available=previous_state is not None,
            metadata=metadata or {}
        )

        self.save_state(state)
        utils.log_info(f"🆕 New deployment created: {deployment_id}")

        return state

    def update_status(self, status: DeploymentStatus) -> None:
        """
        Update deployment status.

        Args:
            status: New deployment status
        """
        if self.current_state is None:
            raise ValueError("No current deployment state loaded")

        self.current_state.status = status
        self.save_state(self.current_state)

    def add_service(
        self,
        service_name: str,
        version: Optional[str] = None,
        image: Optional[str] = None,
        ports: Optional[List[int]] = None
    ) -> None:
        """
        Add or update a service in deployment state.

        Args:
            service_name: Name of the service
            version: Service version
            image: Docker image
            ports: List of ports
        """
        if self.current_state is None:
            raise ValueError("No current deployment state loaded")

        service_state = ServiceState(
            name=service_name,
            status=ServiceStatus.STARTING,
            version=version,
            image=image,
            ports=ports or [],
            last_updated=datetime.utcnow().isoformat() + "Z"
        )

        self.current_state.services[service_name] = service_state
        self.save_state(self.current_state)
        utils.log_info(f"➕ Service added to state: {service_name}")

    def update_service_status(
        self,
        service_name: str,
        status: ServiceStatus,
        increment_failures: bool = False
    ) -> None:
        """
        Update service health status.

        Args:
            service_name: Name of the service
            status: New service status
            increment_failures: Whether to increment health check failures
        """
        if self.current_state is None:
            raise ValueError("No current deployment state loaded")

        if service_name not in self.current_state.services:
            utils.log_warn(f"Service {service_name} not found in state")
            return

        service = self.current_state.services[service_name]
        service.status = status
        service.last_updated = datetime.utcnow().isoformat() + "Z"

        if increment_failures:
            service.health_check_failures += 1

        # Reset failures on healthy status
        if status == ServiceStatus.HEALTHY:
            service.health_check_failures = 0

        self.save_state(self.current_state)

    def set_environment_hash(self, service_name: str, env_hash: str) -> None:
        """
        Set environment hash for a service (for change detection).

        Args:
            service_name: Name of the service
            env_hash: Hash of environment configuration
        """
        if self.current_state is None:
            raise ValueError("No current deployment state loaded")

        if service_name not in self.current_state.services:
            utils.log_warn(f"Service {service_name} not found in state")
            return

        self.current_state.services[service_name].environment_hash = env_hash
        self.save_state(self.current_state)

    def is_deployment_running(self) -> bool:
        """
        Check if a deployment is currently running.

        Returns:
            True if deployment exists and is running
        """
        if self.current_state is None:
            return False

        return self.current_state.status == DeploymentStatus.RUNNING

    def requires_update(self, service_name: str, new_env_hash: str) -> bool:
        """
        Check if service requires update based on environment hash.

        Args:
            service_name: Name of the service
            new_env_hash: New environment hash

        Returns:
            True if service needs update
        """
        if self.current_state is None:
            return True  # No state = fresh deployment

        if service_name not in self.current_state.services:
            return True  # Service not deployed yet

        service = self.current_state.services[service_name]
        return service.environment_hash != new_env_hash

    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """
        Get current status of a service.

        Args:
            service_name: Name of the service

        Returns:
            ServiceStatus if service exists, None otherwise
        """
        if self.current_state is None:
            return None

        service = self.current_state.services.get(service_name)
        return service.status if service else None

    def get_unhealthy_services(self) -> List[str]:
        """
        Get list of unhealthy services.

        Returns:
            List of unhealthy service names
        """
        if self.current_state is None:
            return []

        return [
            name for name, service in self.current_state.services.items()
            if service.status in [ServiceStatus.UNHEALTHY, ServiceStatus.STOPPED]
        ]

    def mark_rollback_started(self) -> None:
        """Mark that rollback process has started."""
        if self.current_state:
            self.current_state.status = DeploymentStatus.ROLLING_BACK
            self.save_state(self.current_state)

    def mark_rollback_complete(self) -> None:
        """Mark that rollback process has completed."""
        if self.current_state:
            self.current_state.status = DeploymentStatus.ROLLED_BACK
            self.save_state(self.current_state)

    def get_previous_state(self) -> Optional[DeploymentState]:
        """
        Get the previous deployment state (for rollback).

        Returns:
            Previous DeploymentState if available
        """
        if not self.current_state or not self.current_state.previous_deployment_id:
            return None

        # Look for backup with matching deployment ID
        backups = sorted(self.backup_dir.glob("state-*.json"), reverse=True)

        for backup in backups:
            try:
                with open(backup, 'r') as f:
                    data = json.load(f)

                if data.get('deployment_id') == self.current_state.previous_deployment_id:
                    return DeploymentState.from_dict(data)

            except Exception as e:
                utils.log_warn(f"Failed to load backup {backup}: {e}")

        return None

    def export_state_report(self, output_file: Path) -> None:
        """
        Export deployment state report to JSON.

        Args:
            output_file: Path to output file
        """
        if self.current_state is None:
            utils.log_warn("No deployment state to export")
            return

        report = {
            "deployment": self.current_state.to_dict(),
            "health_summary": {
                "total_services": len(self.current_state.services),
                "healthy": len([s for s in self.current_state.services.values()
                               if s.status == ServiceStatus.HEALTHY]),
                "unhealthy": len([s for s in self.current_state.services.values()
                                 if s.status == ServiceStatus.UNHEALTHY]),
                "stopped": len([s for s in self.current_state.services.values()
                               if s.status == ServiceStatus.STOPPED]),
                "unknown": len([s for s in self.current_state.services.values()
                               if s.status == ServiceStatus.UNKNOWN]),
            },
            "rollback_info": {
                "available": self.current_state.rollback_available,
                "previous_deployment": self.current_state.previous_deployment_id
            }
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        utils.log_info(f"📄 State report exported to: {output_file}")


def get_deployment_state(tenant: str) -> Optional[DeploymentState]:
    """
    Get current deployment state for a tenant.

    Args:
        tenant: Tenant name

    Returns:
        DeploymentState if exists, None otherwise
    """
    manager = DeploymentStateManager(tenant)
    return manager.load_state()


def is_deployment_active(tenant: str) -> bool:
    """
    Check if tenant has an active deployment.

    Args:
        tenant: Tenant name

    Returns:
        True if deployment is active
    """
    state = get_deployment_state(tenant)
    return state is not None and state.status == DeploymentStatus.RUNNING
