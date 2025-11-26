"""
Secrets Management Module

Handles secure credential encryption, transfer, and injection into deployments.
Integrates with existing credential_manager for generation and provides
secure distribution to target VMs.
"""

import base64
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import constants, utils


class SecretsError(Exception):
    """Raised when secrets operations fail."""
    pass


class SecretsManager:
    """Manages secure credential distribution and injection."""

    def __init__(self, tenant: str):
        """
        Initialize secrets manager.

        Args:
            tenant: Tenant name
        """
        self.tenant = tenant
        self.tenant_dir = constants.MS_CONFIG_DIR / "tenants" / tenant
        self.secrets_dir = self.tenant_dir / "secrets"
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

    def encrypt_credentials(
        self,
        credentials_dir: Path,
        encryption_key: Optional[str] = None
    ) -> Path:
        """
        Encrypt credentials directory into a secure bundle.

        Args:
            credentials_dir: Directory containing credential files
            encryption_key: Optional encryption key (auto-generated if not provided)

        Returns:
            Path to encrypted bundle

        Raises:
            SecretsError: If encryption fails
        """
        utils.log_info(f"🔐 Encrypting credentials for tenant: {self.tenant}")

        if not credentials_dir.exists():
            raise SecretsError(f"Credentials directory not found: {credentials_dir}")

        # Generate encryption key if not provided
        if encryption_key is None:
            encryption_key = self._generate_encryption_key()
            utils.log_info("🔑 Generated new encryption key")

        try:
            # Create tar.gz archive of credentials
            timestamp = utils.get_timestamp()
            bundle_name = f"credentials-{timestamp}"
            bundle_path = self.secrets_dir / f"{bundle_name}.tar.gz.enc"
            temp_archive = self.secrets_dir / f"{bundle_name}.tar.gz"

            # Create tar archive
            with tarfile.open(temp_archive, 'w:gz') as tar:
                tar.add(credentials_dir, arcname=bundle_name)

            # Encrypt with openssl (AES-256-CBC)
            self._encrypt_file(temp_archive, bundle_path, encryption_key)

            # Remove temporary unencrypted archive
            temp_archive.unlink()

            # Save encryption key separately (for operator reference)
            key_file = self.secrets_dir / f"{bundle_name}.key"
            with open(key_file, 'w') as f:
                f.write(encryption_key)

            # Restrict permissions
            os.chmod(bundle_path, 0o600)
            os.chmod(key_file, 0o600)

            utils.log_success(f"✅ Credentials encrypted: {bundle_path}")
            utils.log_info(f"   Encryption key saved to: {key_file}")
            utils.log_warn("⚠️  Keep the encryption key secure!")

            return bundle_path

        except Exception as e:
            raise SecretsError(f"Failed to encrypt credentials: {e}") from e

    def _encrypt_file(self, input_file: Path, output_file: Path, key: str) -> None:
        """
        Encrypt file using OpenSSL AES-256-CBC.

        Args:
            input_file: File to encrypt
            output_file: Encrypted output file
            key: Encryption key
        """
        try:
            cmd = [
                "openssl", "enc", "-aes-256-cbc",
                "-salt",
                "-in", str(input_file),
                "-out", str(output_file),
                "-k", key
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode != 0:
                raise SecretsError(f"OpenSSL encryption failed: {result.stderr}")

        except FileNotFoundError:
            raise SecretsError("OpenSSL not found. Install with: apt install openssl")
        except subprocess.CalledProcessError as e:
            raise SecretsError(f"Encryption failed: {e.stderr}") from e

    def _decrypt_file(self, input_file: Path, output_file: Path, key: str) -> None:
        """
        Decrypt file using OpenSSL AES-256-CBC.

        Args:
            input_file: Encrypted file
            output_file: Decrypted output file
            key: Decryption key
        """
        try:
            cmd = [
                "openssl", "enc", "-aes-256-cbc", "-d",
                "-in", str(input_file),
                "-out", str(output_file),
                "-k", key
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode != 0:
                raise SecretsError(f"OpenSSL decryption failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            raise SecretsError(f"Decryption failed: {e.stderr}") from e

    def _generate_encryption_key(self) -> str:
        """
        Generate a secure random encryption key.

        Returns:
            Base64-encoded random key
        """
        random_bytes = os.urandom(32)  # 256 bits
        return base64.b64encode(random_bytes).decode('utf-8')

    def transfer_to_vm(
        self,
        encrypted_bundle: Path,
        encryption_key: str,
        vm_host: str,
        vm_user: str,
        remote_dir: str = "/tmp"
    ) -> Tuple[str, str]:
        """
        Transfer encrypted credentials to target VM.

        Args:
            encrypted_bundle: Path to encrypted credential bundle
            encryption_key: Encryption key
            vm_host: VM hostname or IP
            vm_user: SSH username
            remote_dir: Remote directory for temporary storage

        Returns:
            Tuple of (remote_bundle_path, remote_key_path)

        Raises:
            SecretsError: If transfer fails
        """
        utils.log_info(f"📤 Transferring credentials to {vm_host}...")

        if not encrypted_bundle.exists():
            raise SecretsError(f"Encrypted bundle not found: {encrypted_bundle}")

        try:
            # Create remote temporary directory
            remote_temp = f"{remote_dir}/paas-secrets-{self.tenant}"
            utils.ssh_command(vm_host, vm_user, f"mkdir -p {remote_temp}", check=True)

            # Transfer encrypted bundle
            remote_bundle = f"{remote_temp}/{encrypted_bundle.name}"
            utils.scp_upload(vm_host, vm_user, str(encrypted_bundle), remote_bundle)
            utils.log_info(f"✅ Bundle transferred to: {remote_bundle}")

            # Create key file on remote (more secure than transferring)
            remote_key = f"{remote_temp}/decryption.key"
            key_cmd = f"echo '{encryption_key}' > {remote_key} && chmod 600 {remote_key}"
            utils.ssh_command(vm_host, vm_user, key_cmd, check=True)
            utils.log_info(f"✅ Decryption key created on VM")

            # Secure the remote directory
            utils.ssh_command(vm_host, vm_user, f"chmod 700 {remote_temp}", check=True)

            return remote_bundle, remote_key

        except Exception as e:
            raise SecretsError(f"Failed to transfer credentials: {e}") from e

    def decrypt_and_inject_on_vm(
        self,
        vm_host: str,
        vm_user: str,
        remote_bundle: str,
        remote_key: str,
        target_dir: str = "~/paas-deployment"
    ) -> bool:
        """
        Decrypt credentials on VM and inject into deployment directory.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
            remote_bundle: Path to encrypted bundle on VM
            remote_key: Path to decryption key on VM
            target_dir: Target directory for decrypted credentials

        Returns:
            True if successful

        Raises:
            SecretsError: If decryption/injection fails
        """
        utils.log_info(f"🔓 Decrypting and injecting credentials on VM...")

        try:
            # Decrypt on remote
            decrypted_archive = remote_bundle.replace('.enc', '')
            decrypt_cmd = f"openssl enc -aes-256-cbc -d -in {remote_bundle} -out {decrypted_archive} -k $(cat {remote_key})"

            result = utils.ssh_command(vm_host, vm_user, decrypt_cmd, check=False)

            if result.returncode != 0:
                raise SecretsError(f"Remote decryption failed: {result.stderr}")

            utils.log_info("✅ Credentials decrypted on VM")

            # Extract archive
            remote_temp_dir = str(Path(remote_bundle).parent)
            extract_cmd = f"cd {remote_temp_dir} && tar -xzf {decrypted_archive}"
            utils.ssh_command(vm_host, vm_user, extract_cmd, check=True)

            # Find extracted directory
            ls_cmd = f"ls -d {remote_temp_dir}/credentials-*/ | head -1"
            result = utils.ssh_command(vm_host, vm_user, ls_cmd, check=False)

            if result.returncode != 0:
                raise SecretsError("Could not find extracted credentials directory")

            extracted_dir = result.stdout.strip()

            # Create target directory
            utils.ssh_command(vm_host, vm_user, f"mkdir -p {target_dir}", check=True)

            # Copy credential files to target
            copy_cmd = f"cp -r {extracted_dir}/*.env {target_dir}/ || true"
            utils.ssh_command(vm_host, vm_user, copy_cmd, check=True)

            # Set restrictive permissions
            chmod_cmd = f"chmod 600 {target_dir}/*.env"
            utils.ssh_command(vm_host, vm_user, chmod_cmd, check=True)

            utils.log_success(f"✅ Credentials injected to: {target_dir}")

            # Cleanup temporary files
            self._cleanup_remote_secrets(vm_host, vm_user, remote_temp_dir)

            return True

        except Exception as e:
            raise SecretsError(f"Failed to decrypt/inject credentials: {e}") from e

    def _cleanup_remote_secrets(self, vm_host: str, vm_user: str, remote_dir: str) -> None:
        """
        Securely cleanup temporary credential files on remote VM.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
            remote_dir: Directory to cleanup
        """
        utils.log_info("🧹 Cleaning up temporary credential files...")

        try:
            # Securely overwrite files before deletion
            cleanup_script = f"""
cd {remote_dir} || exit 0
for file in *.enc *.tar.gz *.key; do
    [ -f "$file" ] && shred -vfz -n 3 "$file" || true
done
cd ..
rm -rf {remote_dir}
"""
            utils.ssh_command(vm_host, vm_user, cleanup_script, check=False)
            utils.log_info("✅ Temporary files securely removed")

        except Exception as e:
            utils.log_warn(f"Failed to cleanup remote files: {e}")

    def rotate_credentials(
        self,
        vm_host: str,
        vm_user: str,
        services: Optional[List[str]] = None
    ) -> bool:
        """
        Rotate credentials for specified services.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
            services: List of services to rotate (all if None)

        Returns:
            True if rotation successful
        """
        utils.log_info(f"🔄 Rotating credentials for tenant: {self.tenant}")

        # This would integrate with credential_manager to generate new credentials
        # For now, this is a placeholder for the rotation workflow

        utils.log_warn("⚠️  Credential rotation not yet implemented")
        utils.log_info("   Workflow:")
        utils.log_info("   1. Generate new credentials")
        utils.log_info("   2. Update service configurations")
        utils.log_info("   3. Restart services with new credentials")
        utils.log_info("   4. Verify service health")
        utils.log_info("   5. Revoke old credentials")

        return False

    def validate_credential_injection(
        self,
        vm_host: str,
        vm_user: str,
        target_dir: str = "~/paas-deployment"
    ) -> bool:
        """
        Validate that credentials were properly injected.

        Args:
            vm_host: VM hostname or IP
            vm_user: SSH username
            target_dir: Directory to check

        Returns:
            True if credentials are present and valid
        """
        utils.log_info("🔍 Validating credential injection...")

        expected_files = [
            f"{target_dir}/.env",
            f"{target_dir}/credentials.env"
        ]

        all_present = True

        for file_path in expected_files:
            check_cmd = f"test -f {file_path} && echo 'exists' || echo 'missing'"
            result = utils.ssh_command(vm_host, vm_user, check_cmd, check=False)

            if "exists" in result.stdout:
                # Check file is not empty
                size_cmd = f"stat -c %s {file_path}"
                size_result = utils.ssh_command(vm_host, vm_user, size_cmd, check=False)

                if size_result.returncode == 0:
                    size = int(size_result.stdout.strip())
                    if size > 0:
                        utils.log_info(f"✅ {file_path} ({size} bytes)")
                    else:
                        utils.log_warn(f"⚠️  {file_path} is empty")
                        all_present = False
            else:
                utils.log_warn(f"❌ {file_path} not found")
                all_present = False

        if all_present:
            utils.log_success("✅ All credential files validated")
        else:
            utils.log_warn("⚠️  Some credential files are missing or invalid")

        return all_present

    def compute_env_hash(self, env_file: Path) -> str:
        """
        Compute hash of environment file for change detection.

        Args:
            env_file: Path to .env file

        Returns:
            SHA256 hash of file contents
        """
        if not env_file.exists():
            return ""

        hasher = hashlib.sha256()

        with open(env_file, 'rb') as f:
            hasher.update(f.read())

        return hasher.hexdigest()


def deploy_secrets_to_vm(
    tenant: str,
    credentials_dir: Path,
    vm_host: str,
    vm_user: str,
    target_dir: str = "~/paas-deployment"
) -> bool:
    """
    Complete workflow: encrypt, transfer, and inject credentials to VM.

    Args:
        tenant: Tenant name
        credentials_dir: Directory containing generated credentials
        vm_host: VM hostname or IP
        vm_user: SSH username
        target_dir: Target directory on VM

    Returns:
        True if successful
    """
    secrets_mgr = SecretsManager(tenant)

    try:
        # Step 1: Encrypt credentials
        encrypted_bundle = secrets_mgr.encrypt_credentials(credentials_dir)

        # Step 2: Get encryption key
        key_file = encrypted_bundle.with_suffix('.key')
        with open(key_file, 'r') as f:
            encryption_key = f.read().strip()

        # Step 3: Transfer to VM
        remote_bundle, remote_key = secrets_mgr.transfer_to_vm(
            encrypted_bundle,
            encryption_key,
            vm_host,
            vm_user
        )

        # Step 4: Decrypt and inject on VM
        success = secrets_mgr.decrypt_and_inject_on_vm(
            vm_host,
            vm_user,
            remote_bundle,
            remote_key,
            target_dir
        )

        # Step 5: Validate injection
        if success:
            secrets_mgr.validate_credential_injection(vm_host, vm_user, target_dir)

        return success

    except SecretsError as e:
        utils.log_error(f"Secret deployment failed: {e}")
        return False
