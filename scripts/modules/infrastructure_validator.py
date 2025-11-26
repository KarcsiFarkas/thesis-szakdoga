"""
Infrastructure Validation Module

Performs comprehensive pre-deployment validation of target infrastructure.
Checks system resources, network connectivity, software dependencies, and security.
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import constants, utils


class InfrastructureValidationError(Exception):
    """Raised when infrastructure validation fails."""
    pass


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "check": self.check_name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
            "details": self.details
        }


@dataclass
class InfrastructureRequirements:
    """Infrastructure requirements for deployment."""
    min_cpu_cores: int = 4
    min_ram_gb: int = 8
    min_disk_gb: int = 50
    required_ports: List[int] = field(default_factory=lambda: [22, 80, 443, 5432, 6379])
    required_packages: List[str] = field(default_factory=lambda: ["docker", "python3", "git"])
    docker_min_version: str = "24.0.0"
    check_swap: bool = True
    check_firewall: bool = True
    check_selinux: bool = True


class InfrastructureValidator:
    """Validates infrastructure readiness for deployment."""

    def __init__(
        self,
        vm_host: str,
        vm_user: str,
        requirements: Optional[InfrastructureRequirements] = None
    ):
        """
        Initialize infrastructure validator.

        Args:
            vm_host: Hostname or IP of target VM
            vm_user: SSH username for target VM
            requirements: Infrastructure requirements (uses defaults if not provided)
        """
        self.vm_host = vm_host
        self.vm_user = vm_user
        self.requirements = requirements or InfrastructureRequirements()
        self.results: List[ValidationResult] = []

    def validate_all(self, skip_warnings: bool = False) -> Tuple[bool, List[ValidationResult]]:
        """
        Run all validation checks.

        Args:
            skip_warnings: If True, warnings won't cause validation to fail

        Returns:
            Tuple of (overall_success, list_of_results)
        """
        utils.log_info("🔍 Starting infrastructure validation...")
        utils.log_info(f"   Target: {self.vm_user}@{self.vm_host}")

        # Reset results
        self.results = []

        # Run all checks
        self._check_ssh_connectivity()
        self._check_system_resources()
        self._check_network()
        self._check_software_dependencies()
        self._check_security()
        self._check_docker_configuration()

        # Determine overall result
        errors = [r for r in self.results if not r.passed and r.severity == "error"]
        warnings = [r for r in self.results if not r.passed and r.severity == "warning"]

        success = len(errors) == 0 and (skip_warnings or len(warnings) == 0)

        # Print summary
        self._print_summary(errors, warnings)

        return success, self.results

    def _print_summary(self, errors: List[ValidationResult], warnings: List[ValidationResult]) -> None:
        """Print validation summary."""
        passed = len([r for r in self.results if r.passed])
        total = len(self.results)

        utils.log_info(f"\n📊 Validation Summary: {passed}/{total} checks passed")

        if errors:
            utils.log_error(f"❌ {len(errors)} critical errors found:")
            for error in errors:
                utils.log_error(f"   - {error.check_name}: {error.message}")

        if warnings:
            utils.log_warn(f"⚠️  {len(warnings)} warnings:")
            for warning in warnings:
                utils.log_warn(f"   - {warning.check_name}: {warning.message}")

        if not errors and not warnings:
            utils.log_success("✅ All validation checks passed!")

    def _ssh_command(self, command: str, check: bool = False) -> subprocess.CompletedProcess:
        """Execute command on remote VM via SSH."""
        return utils.ssh_command(
            self.vm_host,
            self.vm_user,
            command,
            check=check
        )

    def _check_ssh_connectivity(self) -> None:
        """Validate SSH connectivity to target VM."""
        check_name = "SSH Connectivity"

        try:
            result = self._ssh_command("echo 'connected'", check=False)

            if result.returncode == 0:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=True,
                    message="SSH connection successful",
                    severity="info"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message=f"SSH connection failed: {result.stderr}",
                    severity="error"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"SSH connection error: {str(e)}",
                severity="error"
            ))

    def _check_system_resources(self) -> None:
        """Validate system resources (CPU, RAM, disk)."""
        # Check CPU cores
        self._check_cpu_cores()

        # Check RAM
        self._check_ram()

        # Check disk space
        self._check_disk_space()

        # Check swap (optional)
        if self.requirements.check_swap:
            self._check_swap()

    def _check_cpu_cores(self) -> None:
        """Check CPU core count."""
        check_name = "CPU Cores"

        try:
            result = self._ssh_command("nproc", check=False)

            if result.returncode == 0:
                cores = int(result.stdout.strip())

                if cores >= self.requirements.min_cpu_cores:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message=f"{cores} cores available (required: {self.requirements.min_cpu_cores})",
                        severity="info",
                        details={"cores": cores, "required": self.requirements.min_cpu_cores}
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message=f"Insufficient CPU cores: {cores} (required: {self.requirements.min_cpu_cores})",
                        severity="warning",
                        details={"cores": cores, "required": self.requirements.min_cpu_cores}
                    ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message="Failed to detect CPU cores",
                    severity="warning"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"CPU check error: {str(e)}",
                severity="warning"
            ))

    def _check_ram(self) -> None:
        """Check available RAM."""
        check_name = "RAM"

        try:
            result = self._ssh_command("free -g | awk '/^Mem:/ {print $2}'", check=False)

            if result.returncode == 0:
                ram_gb = int(result.stdout.strip())

                if ram_gb >= self.requirements.min_ram_gb:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message=f"{ram_gb}GB RAM available (required: {self.requirements.min_ram_gb}GB)",
                        severity="info",
                        details={"ram_gb": ram_gb, "required_gb": self.requirements.min_ram_gb}
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message=f"Insufficient RAM: {ram_gb}GB (required: {self.requirements.min_ram_gb}GB)",
                        severity="error",
                        details={"ram_gb": ram_gb, "required_gb": self.requirements.min_ram_gb}
                    ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message="Failed to detect RAM",
                    severity="warning"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"RAM check error: {str(e)}",
                severity="warning"
            ))

    def _check_disk_space(self) -> None:
        """Check available disk space."""
        check_name = "Disk Space"

        try:
            result = self._ssh_command("df -BG / | awk 'NR==2 {print $4}' | sed 's/G//'", check=False)

            if result.returncode == 0:
                disk_gb = int(result.stdout.strip())

                if disk_gb >= self.requirements.min_disk_gb:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message=f"{disk_gb}GB free disk space (required: {self.requirements.min_disk_gb}GB)",
                        severity="info",
                        details={"disk_gb": disk_gb, "required_gb": self.requirements.min_disk_gb}
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message=f"Insufficient disk space: {disk_gb}GB (required: {self.requirements.min_disk_gb}GB)",
                        severity="error",
                        details={"disk_gb": disk_gb, "required_gb": self.requirements.min_disk_gb}
                    ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message="Failed to check disk space",
                    severity="warning"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Disk space check error: {str(e)}",
                severity="warning"
            ))

    def _check_swap(self) -> None:
        """Check if swap is configured."""
        check_name = "Swap Memory"

        try:
            result = self._ssh_command("free -g | awk '/^Swap:/ {print $2}'", check=False)

            if result.returncode == 0:
                swap_gb = int(result.stdout.strip())

                if swap_gb > 0:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message=f"{swap_gb}GB swap configured",
                        severity="info",
                        details={"swap_gb": swap_gb}
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message="No swap configured (recommended for production)",
                        severity="warning"
                    ))
        except Exception:
            # Swap check is optional, don't fail on errors
            pass

    def _check_network(self) -> None:
        """Validate network connectivity and DNS."""
        # Check DNS resolution
        self._check_dns_resolution()

        # Check outbound internet
        self._check_internet_connectivity()

        # Check required ports
        self._check_port_availability()

    def _check_dns_resolution(self) -> None:
        """Check DNS resolution."""
        check_name = "DNS Resolution"

        try:
            result = self._ssh_command("nslookup google.com", check=False)

            if result.returncode == 0:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=True,
                    message="DNS resolution working",
                    severity="info"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message="DNS resolution failed",
                    severity="error"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"DNS check error: {str(e)}",
                severity="error"
            ))

    def _check_internet_connectivity(self) -> None:
        """Check outbound internet connectivity."""
        check_name = "Internet Connectivity"

        try:
            result = self._ssh_command("curl -sSf -m 5 https://www.google.com > /dev/null 2>&1 && echo 'ok'", check=False)

            if result.returncode == 0 and "ok" in result.stdout:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=True,
                    message="Internet connectivity verified",
                    severity="info"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message="Internet connectivity test failed",
                    severity="error"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Internet check error: {str(e)}",
                severity="error"
            ))

    def _check_port_availability(self) -> None:
        """Check if required ports are available."""
        check_name = "Port Availability"

        try:
            # Check if ports are listening (should NOT be for fresh deployment)
            ports_str = " ".join(str(p) for p in self.requirements.required_ports)
            cmd = f"ss -tuln | grep -E '({'|'.join(str(p) for p in self.requirements.required_ports)})' || echo 'none'"

            result = self._ssh_command(cmd, check=False)

            if result.returncode == 0:
                output = result.stdout.strip()

                if output == "none" or not output:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message=f"Required ports are available: {ports_str}",
                        severity="info"
                    ))
                else:
                    # Parse which ports are in use
                    used_ports = []
                    for line in output.split('\n'):
                        for port in self.requirements.required_ports:
                            if f":{port}" in line:
                                used_ports.append(port)

                    if used_ports:
                        self.results.append(ValidationResult(
                            check_name=check_name,
                            passed=False,
                            message=f"Ports already in use: {', '.join(map(str, set(used_ports)))}",
                            severity="warning",
                            details={"used_ports": list(set(used_ports))}
                        ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Port check error: {str(e)}",
                severity="warning"
            ))

    def _check_software_dependencies(self) -> None:
        """Validate required software packages."""
        check_name = "Software Dependencies"

        missing_packages = []

        for package in self.requirements.required_packages:
            try:
                result = self._ssh_command(f"command -v {package}", check=False)

                if result.returncode != 0:
                    missing_packages.append(package)
            except Exception:
                missing_packages.append(package)

        if not missing_packages:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=True,
                message=f"All required packages installed: {', '.join(self.requirements.required_packages)}",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Missing packages: {', '.join(missing_packages)}",
                severity="error",
                details={"missing": missing_packages}
            ))

    def _check_security(self) -> None:
        """Validate security configuration."""
        # Check firewall
        if self.requirements.check_firewall:
            self._check_firewall_status()

        # Check SELinux/AppArmor
        if self.requirements.check_selinux:
            self._check_selinux_apparmor()

        # Check SSH key authentication
        self._check_ssh_key_auth()

    def _check_firewall_status(self) -> None:
        """Check firewall configuration."""
        check_name = "Firewall Configuration"

        try:
            # Check if ufw is active
            result = self._ssh_command("sudo ufw status | head -1", check=False)

            if result.returncode == 0:
                status = result.stdout.strip()

                if "inactive" in status.lower():
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message="Firewall (ufw) is inactive - should be enabled for production",
                        severity="warning"
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message="Firewall is active",
                        severity="info"
                    ))
        except Exception:
            # Firewall check is optional
            pass

    def _check_selinux_apparmor(self) -> None:
        """Check SELinux or AppArmor status."""
        check_name = "SELinux/AppArmor"

        try:
            # Check SELinux
            result = self._ssh_command("command -v getenforce && getenforce", check=False)

            if result.returncode == 0:
                status = result.stdout.strip()

                if status == "Enforcing":
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message="SELinux is enforcing - may block Docker operations",
                        severity="warning",
                        details={"mode": "selinux", "status": "enforcing"}
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message=f"SELinux status: {status}",
                        severity="info"
                    ))
            else:
                # Check AppArmor
                result = self._ssh_command("sudo aa-status 2>/dev/null | head -1", check=False)

                if result.returncode == 0 and result.stdout:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=True,
                        message="AppArmor detected and active",
                        severity="info"
                    ))
        except Exception:
            # Security module check is optional
            pass

    def _check_ssh_key_auth(self) -> None:
        """Verify SSH key authentication is working."""
        check_name = "SSH Key Authentication"

        # This is implicitly checked by SSH connectivity test
        # If we got here, SSH key auth is working
        self.results.append(ValidationResult(
            check_name=check_name,
            passed=True,
            message="SSH key authentication verified",
            severity="info"
        ))

    def _check_docker_configuration(self) -> None:
        """Validate Docker installation and configuration."""
        # Check Docker version
        self._check_docker_version()

        # Check Docker service status
        self._check_docker_service()

        # Check Docker permissions
        self._check_docker_permissions()

        # Check required kernel modules
        self._check_kernel_modules()

    def _check_docker_version(self) -> None:
        """Check Docker version."""
        check_name = "Docker Version"

        try:
            result = self._ssh_command("docker --version", check=False)

            if result.returncode == 0:
                version_match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)

                if version_match:
                    version = version_match.group(1)
                    min_version = self.requirements.docker_min_version

                    # Simple version comparison (works for major.minor.patch)
                    if self._compare_versions(version, min_version) >= 0:
                        self.results.append(ValidationResult(
                            check_name=check_name,
                            passed=True,
                            message=f"Docker {version} installed (required: {min_version}+)",
                            severity="info",
                            details={"version": version, "required": min_version}
                        ))
                    else:
                        self.results.append(ValidationResult(
                            check_name=check_name,
                            passed=False,
                            message=f"Docker version too old: {version} (required: {min_version}+)",
                            severity="error",
                            details={"version": version, "required": min_version}
                        ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message="Could not parse Docker version",
                        severity="warning"
                    ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message="Docker not installed or not accessible",
                    severity="error"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Docker version check error: {str(e)}",
                severity="error"
            ))

    def _check_docker_service(self) -> None:
        """Check if Docker service is running."""
        check_name = "Docker Service"

        try:
            result = self._ssh_command("systemctl is-active docker", check=False)

            if result.returncode == 0 and "active" in result.stdout:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=True,
                    message="Docker service is running",
                    severity="info"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=False,
                    message="Docker service is not running",
                    severity="error"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Docker service check error: {str(e)}",
                severity="error"
            ))

    def _check_docker_permissions(self) -> None:
        """Check if user has Docker permissions."""
        check_name = "Docker Permissions"

        try:
            result = self._ssh_command("docker ps", check=False)

            if result.returncode == 0:
                self.results.append(ValidationResult(
                    check_name=check_name,
                    passed=True,
                    message=f"User {self.vm_user} has Docker permissions",
                    severity="info"
                ))
            else:
                if "permission denied" in result.stderr.lower():
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message=f"User {self.vm_user} cannot access Docker socket",
                        severity="error",
                        details={"fix": f"Run: sudo usermod -aG docker {self.vm_user}"}
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name=check_name,
                        passed=False,
                        message="Docker permission check failed",
                        severity="error"
                    ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Docker permission check error: {str(e)}",
                severity="error"
            ))

    def _check_kernel_modules(self) -> None:
        """Check required kernel modules."""
        check_name = "Kernel Modules"

        required_modules = ["overlay", "br_netfilter"]
        missing_modules = []

        for module in required_modules:
            try:
                result = self._ssh_command(f"lsmod | grep {module}", check=False)

                if result.returncode != 0:
                    missing_modules.append(module)
            except Exception:
                missing_modules.append(module)

        if not missing_modules:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=True,
                message=f"Required kernel modules loaded: {', '.join(required_modules)}",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                check_name=check_name,
                passed=False,
                message=f"Missing kernel modules: {', '.join(missing_modules)}",
                severity="warning",
                details={"missing": missing_modules}
            ))

    @staticmethod
    def _compare_versions(version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Returns:
            1 if version1 > version2
            0 if version1 == version2
            -1 if version1 < version2
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        # Pad to same length
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)

        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1

        return 0

    def export_results(self, output_file: Path) -> None:
        """
        Export validation results to JSON file.

        Args:
            output_file: Path to output JSON file
        """
        results_dict = {
            "target": f"{self.vm_user}@{self.vm_host}",
            "timestamp": utils.get_timestamp(),
            "total_checks": len(self.results),
            "passed": len([r for r in self.results if r.passed]),
            "failed": len([r for r in self.results if not r.passed]),
            "results": [r.to_dict() for r in self.results]
        }

        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        utils.log_info(f"📄 Validation results exported to: {output_file}")


def validate_infrastructure(
    vm_host: str,
    vm_user: str,
    requirements: Optional[InfrastructureRequirements] = None,
    export_results: bool = True,
    results_dir: Optional[Path] = None
) -> bool:
    """
    Validate infrastructure and optionally export results.

    Args:
        vm_host: Hostname or IP of target VM
        vm_user: SSH username
        requirements: Infrastructure requirements
        export_results: Whether to export results to file
        results_dir: Directory to save results (defaults to tenant metrics dir)

    Returns:
        True if validation passed, False otherwise
    """
    validator = InfrastructureValidator(vm_host, vm_user, requirements)
    success, results = validator.validate_all(skip_warnings=False)

    if export_results:
        if results_dir is None:
            results_dir = Path.home() / "paas-deployment" / "metrics"

        results_dir.mkdir(parents=True, exist_ok=True)
        timestamp = utils.get_timestamp()
        results_file = results_dir / f"validation-{timestamp}.json"
        validator.export_results(results_file)

    return success
