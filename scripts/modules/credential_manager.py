"""
Credential Management Module for PaaS Deployment

Handles generation, storage, and import of service credentials.
Integrates with the credential generation script and Bitwarden CLI.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from . import utils, constants


class CredentialManagerError(Exception):
    """Raised when credential operations fail."""
    pass


def generate_credentials(tenant_name: str, global_password: Optional[str] = None) -> Path:
    """
    Generate credentials for all services and databases.

    Args:
        tenant_name: Name of the tenant
        global_password: Optional global password (required if password_mode != 'generate')

    Returns:
        Path to the temp-auth directory containing generated credentials

    Raises:
        CredentialManagerError: If credential generation fails
    """
    utils.log_info(f"🔐 Generating credentials for tenant: {tenant_name}")

    # Build credential generation script path
    cred_script = constants.ROOT_DIR / "tools" / "generate-credentials.sh"

    if not cred_script.exists():
        raise CredentialManagerError(f"Credential generation script not found: {cred_script}")

    # Prepare environment
    env = os.environ.copy()
    if global_password:
        env["GLOBAL_PASSWORD"] = global_password

    # Execute credential generation script
    try:
        result = subprocess.run(
            [str(cred_script), tenant_name],
            env=env,
            stdin=subprocess.DEVNULL,  # Don't inherit stdin
            capture_output=True,
            text=True,
            check=True
        )

        # The script outputs the temp-auth directory path as the last line
        temp_auth_dir = Path(result.stdout.strip().split('\n')[-1])

        if not temp_auth_dir.exists():
            raise CredentialManagerError(f"Expected temp-auth directory not created: {temp_auth_dir}")

        utils.log_success(f"✅ Credentials generated successfully: {temp_auth_dir}")
        return temp_auth_dir

    except subprocess.CalledProcessError as e:
        utils.log_error(f"Credential generation failed: {e.stderr}")
        raise CredentialManagerError(f"Failed to generate credentials: {e.stderr}") from e


def wait_for_vaultwarden(
    container_name: str = "vaultwarden",
    timeout: int = 120,
    check_interval: int = 5
) -> bool:
    """
    Wait for Vaultwarden container to be ready.

    Args:
        container_name: Name of the Vaultwarden container
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds

    Returns:
        True if Vaultwarden is ready, False if timeout

    Raises:
        CredentialManagerError: If Docker is not available
    """
    utils.log_info(f"⏳ Waiting for Vaultwarden container '{container_name}'...")

    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            result = subprocess.run(
                ["docker", "container", "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0 and "true" in result.stdout.lower():
                utils.log_success(f"✅ Vaultwarden container is ready")
                # Give it a few more seconds to fully initialize
                time.sleep(5)
                return True

        except FileNotFoundError:
            raise CredentialManagerError("Docker is not available. Is it installed and running?")

        time.sleep(check_interval)

    utils.log_warn(f"⚠️  Timeout waiting for Vaultwarden container (waited {timeout}s)")
    return False


def import_to_bitwarden(
    temp_auth_dir: Path,
    vaultwarden_url: str,
    bw_client_id: Optional[str] = None,
    bw_client_secret: Optional[str] = None,
    bw_password: Optional[str] = None,
    auto_cleanup: bool = True
) -> bool:
    """
    Import credentials to Bitwarden/Vaultwarden using the CLI.

    Args:
        temp_auth_dir: Path to temp-auth directory with credentials
        vaultwarden_url: URL of the Vaultwarden instance
        bw_client_id: Bitwarden API client ID (optional, can use env var)
        bw_client_secret: Bitwarden API client secret (optional, can use env var)
        bw_password: Bitwarden master password (optional, can use env var)
        auto_cleanup: Whether to cleanup temp-auth directory after successful import

    Returns:
        True if import successful, False otherwise

    Raises:
        CredentialManagerError: If bw CLI is not available or configuration is invalid
    """
    utils.log_info("📥 Importing credentials to Bitwarden...")

    # Check if bw CLI is available
    if not utils.command_exists("bw"):
        raise CredentialManagerError(
            "Bitwarden CLI (bw) is not installed. "
            "Run 'chezmoi apply' or install manually from: "
            "https://bitwarden.com/help/cli/"
        )

    # Locate import file
    import_json = temp_auth_dir / "bitwarden-import.json"
    if not import_json.exists():
        raise CredentialManagerError(f"Bitwarden import file not found: {import_json}")

    # Prepare environment variables
    env = os.environ.copy()
    if bw_client_id:
        env["BW_CLIENTID"] = bw_client_id
    if bw_client_secret:
        env["BW_CLIENTSECRET"] = bw_client_secret
    if bw_password:
        env["BW_PASSWORD"] = bw_password

    # Validate required environment variables
    required_vars = ["BW_CLIENTID", "BW_CLIENTSECRET", "BW_PASSWORD"]
    missing_vars = [var for var in required_vars if var not in env]

    if missing_vars:
        raise CredentialManagerError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Set these before importing credentials."
        )

    try:
        # Configure Bitwarden server
        utils.log_info(f"Configuring Bitwarden server: {vaultwarden_url}")
        subprocess.run(
            ["bw", "config", "server", vaultwarden_url],
            check=True,
            capture_output=True,
            env=env
        )

        # Login with API key
        utils.log_info("Authenticating with Bitwarden...")
        subprocess.run(
            ["bw", "login", "--apikey"],
            check=True,
            capture_output=True,
            env=env,
            input=f"{env['BW_CLIENTID']}\n{env['BW_CLIENTSECRET']}".encode()
        )

        # Unlock vault and get session
        result = subprocess.run(
            ["bw", "unlock", "--passwordenv", "BW_PASSWORD", "--raw"],
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
        bw_session = result.stdout.strip()
        env["BW_SESSION"] = bw_session

        # Import credentials
        utils.log_info(f"Importing credentials from {import_json}...")
        subprocess.run(
            ["bw", "import", "bitwardenjson", str(import_json)],
            check=True,
            capture_output=True,
            env=env
        )

        # Verify import by listing items
        result = subprocess.run(
            ["bw", "list", "items"],
            check=True,
            capture_output=True,
            text=True,
            env=env
        )

        items = json.loads(result.stdout)
        utils.log_success(f"✅ Successfully imported {len(items)} credential items to Bitwarden")

        # Logout
        subprocess.run(
            ["bw", "logout"],
            check=False,
            capture_output=True,
            env=env
        )

        # Cleanup temp-auth directory if requested
        if auto_cleanup:
            cleanup_temp_auth(temp_auth_dir)

        return True

    except subprocess.CalledProcessError as e:
        utils.log_error(f"Bitwarden import failed: {e.stderr if e.stderr else 'Unknown error'}")
        utils.log_warn("Credentials remain in temp-auth directory for manual import")
        return False

    except json.JSONDecodeError as e:
        utils.log_error(f"Failed to parse Bitwarden response: {e}")
        return False


def cleanup_temp_auth(temp_auth_dir: Path) -> None:
    """
    Securely cleanup the temporary credentials directory.

    Args:
        temp_auth_dir: Path to temp-auth directory to remove
    """
    if not temp_auth_dir.exists():
        utils.log_warn(f"Temp-auth directory does not exist: {temp_auth_dir}")
        return

    utils.log_info(f"🧹 Cleaning up temporary credentials: {temp_auth_dir}")

    try:
        # Securely overwrite files before deletion (paranoid mode)
        for file_path in temp_auth_dir.glob("*"):
            if file_path.is_file():
                # Overwrite with random data
                file_size = file_path.stat().st_size
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_size))

        # Remove directory
        import shutil
        shutil.rmtree(temp_auth_dir)

        utils.log_success("✅ Temporary credentials cleaned up successfully")

    except Exception as e:
        utils.log_error(f"Failed to cleanup temp-auth directory: {e}")
        utils.log_warn(f"Please manually delete: {temp_auth_dir}")


def load_credentials_env(temp_auth_dir: Path) -> Dict[str, str]:
    """
    Load credentials from the generated credentials.env file.

    Args:
        temp_auth_dir: Path to temp-auth directory

    Returns:
        Dictionary of environment variables from credentials.env

    Raises:
        CredentialManagerError: If credentials file not found or invalid
    """
    creds_file = temp_auth_dir / "credentials.env"

    if not creds_file.exists():
        raise CredentialManagerError(f"Credentials file not found: {creds_file}")

    credentials = {}

    try:
        with open(creds_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    credentials[key.strip()] = value.strip()

        utils.log_info(f"📋 Loaded {len(credentials)} credential entries")
        return credentials

    except Exception as e:
        raise CredentialManagerError(f"Failed to load credentials: {e}") from e


def load_db_credentials_env(temp_auth_dir: Path) -> Dict[str, str]:
    """
    Load database credentials from the generated db-credentials.env file.

    Args:
        temp_auth_dir: Path to temp-auth directory

    Returns:
        Dictionary of environment variables from db-credentials.env

    Raises:
        CredentialManagerError: If database credentials file not found or invalid
    """
    db_creds_file = temp_auth_dir / "db-credentials.env"

    if not db_creds_file.exists():
        raise CredentialManagerError(f"Database credentials file not found: {db_creds_file}")

    db_credentials = {}

    try:
        with open(db_creds_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    db_credentials[key.strip()] = value.strip()

        utils.log_info(f"🗄️  Loaded {len(db_credentials)} database credential entries")
        return db_credentials

    except Exception as e:
        raise CredentialManagerError(f"Failed to load database credentials: {e}") from e
