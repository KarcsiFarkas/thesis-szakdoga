# Thesis PaaS Orchestration System

## Overview

The Thesis PaaS Orchestration System is a comprehensive deployment automation framework for managing self-hosted Platform-as-a-Service (PaaS) infrastructure. It orchestrates the entire lifecycle of multi-tenant environments, from VM provisioning on Proxmox to service deployment using either Docker Compose or NixOS flakes.

### Key Features

- **Multi-Runtime Support**: Deploy services using Docker Compose or NixOS declarative configurations
- **Tenant Isolation**: Full multi-tenant support with per-tenant configuration
- **Proxmox Integration**: Automated VM provisioning with customizable specifications
- **Configuration Management**: YAML-based configuration with validation
- **Service Discovery**: Dynamic Traefik routing configuration
- **Intelligent Remote Execution**: Prefers Mosh over SSH for better connection resilience

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      global-run.py                              │
│                   (Main Orchestrator)                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Config Mgmt  │ │   Proxmox    │ │   Remote     │
│   Module     │ │ Provisioner  │ │  Executor    │
└──────────────┘ └──────────────┘ └──────────────┘
        │              │              │
        ▼              ▼              ▼
┌──────────────────────────────────────────────┐
│          Deployment Runtime Decision         │
└──────────────┬───────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌──────────────┐ ┌──────────────┐
│   Docker     │ │     Nix      │
│   Deployer   │ │   Deployer   │
└──────────────┘ └──────────────┘
        │             │
        ▼             ▼
┌──────────────┐ ┌──────────────┐
│   Traefik    │ │   Flake      │
│   Config     │ │   Staging    │
└──────────────┘ └──────────────┘
```

## Module Documentation

### 1. `constants.py` - Global Constants

**Purpose**: Centralized configuration of all paths, defaults, and system constants.

**Exports**:
- `ROOT_DIR`: Repository root directory
- `MS_CONFIG_DIR`: Tenant configuration directory
- `MGMT_SYSTEM_DIR`: Management system directory
- `OS_INSTALL_DIR`: Proxmox provisioning scripts directory
- `DOCKER_COMPOSE_DIR`: Docker Compose files location
- `NIX_SOLUTION_DIR`: NixOS flake directory
- Various default values and mappings

**Dependencies**: None (base module)

**Configuration**: All paths are derived from the repository root.

### 2. `utils.py` - Utility Functions

**Purpose**: Core utilities for command execution, SSH connectivity, and data parsing.

**Exported Functions**:

```python
class DebugContext:
    """Manages global debug state"""
    @classmethod
    def set_debug(cls, debug: bool) -> None

    @classmethod
    def is_debug(cls) -> bool

def run_command(
    command: list[str],
    cwd: Path,
    env: Optional[dict] = None,
    check: bool = True
) -> subprocess.CompletedProcess
"""Execute commands with debug streaming support"""

def load_proxmox_api_token() -> str
"""Load Proxmox API token from env or file"""

def wait_for_ssh(
    host: str,
    user: str,
    timeout_sec: int = 600,
    interval_sec: int = 10
) -> bool
"""Wait for SSH availability"""

def read_install_config() -> dict
"""Load install_config.yaml"""

def ip_from_cidr(cidr: str) -> str
"""Extract IP from CIDR notation"""

def get_vm_connection_info(vm_name: str) -> tuple[str, dict]
"""Get connection details for a VM"""

def nix_escape_string(s: str) -> str
"""Escape strings for Nix expressions"""
```

**Dependencies**: `constants`

**Usage Example**:
```python
from scripts.modules import utils

utils.DebugContext.set_debug(True)
result = utils.run_command(["ls", "-la"], cwd=Path("/tmp"))
token = utils.load_proxmox_api_token()
```

### 3. `config_manager.py` - Configuration Management

**Purpose**: Configuration validation, loading, and .env generation.

**Exported Functions**:

```python
def lint_configurations(tenant_name: str) -> str
"""Validate all required configuration files"""

def load_tenant_config(tenant_name: str) -> Tuple[Dict, Dict]
"""Load general and selection configs"""

def generate_dotenv(
    general_config: Dict,
    selection_config: Dict,
    services_def: Dict
) -> Path
"""Generate .env.old file for Docker Compose"""

def load_services_definition() -> Dict
"""Load services.json"""

def get_deployment_username(general_config: Dict, vm_name: str) -> str
"""Determine SSH username for deployment"""
```

**Dependencies**: `constants`, `utils`

**Configuration Requirements**:
- `ms-config/tenants/<tenant>/general.conf.yml`
- `ms-config/tenants/<tenant>/selection.yml`
- `management-system/website/services.json` (for Docker runtime)
- `OS_install/configs/install_config.yaml`

**Usage Example**:
```python
from scripts.modules import config_manager

vm_name = config_manager.lint_configurations("test-tenant")
general, selection = config_manager.load_tenant_config("test-tenant")
```

### 4. `proxmox_provisioner.py` - Proxmox VM Provisioning

**Purpose**: Orchestrate Proxmox VM creation and configuration.

**Exported Functions**:

```python
def provision_proxmox_vm(vm_name: str, username: str) -> None
"""Provision a Proxmox VM using provision.py"""
```

**Dependencies**: `constants`, `utils`

**Configuration Requirements**:
- Proxmox API token (env var or proxmox_api.txt)
- `OS_install/provision.py` script
- VM specifications in `OS_install/configs/`

**Usage Example**:
```python
from scripts.modules import proxmox_provisioner

proxmox_provisioner.provision_proxmox_vm("test-vm", "admin")
```

### 5. `remote_executor.py` - Remote Command Execution

**Purpose**: Execute commands on remote hosts via SSH/Mosh with intelligent fallback.

**Exported Functions**:

```python
def has_local_mosh() -> bool
"""Check if mosh is available locally"""

def remote_has_mosh_server(remote: str) -> bool
"""Check if remote has mosh-server"""

def run_remote_prefer_mosh(remote: str, remote_cmd: str) -> subprocess.CompletedProcess
"""Execute remote command preferring mosh"""
```

**Dependencies**: `constants`, `utils`

**Usage Example**:
```python
from scripts.modules import remote_executor

remote_executor.run_remote_prefer_mosh("admin@192.168.1.10", "ls -la")
```

### 6. `docker_deployer.py` - Docker Compose Deployment

**Purpose**: Deploy and manage Docker Compose services with profile support.

**Exported Functions**:

```python
def deploy_services(profiles: List[str], wait_time: int = 0) -> None
"""Deploy specified Docker Compose profiles"""

def deploy_core_services(wait_time: int = 30) -> None
"""Deploy core infrastructure services"""
```

**Dependencies**: `constants`, `utils`

**Configuration Requirements**:
- Docker Compose file at `management-system/docker-compose-solution/`
- Generated .env file with service configuration

**Usage Example**:
```python
from scripts.modules import docker_deployer

docker_deployer.deploy_core_services()
docker_deployer.deploy_services(["media", "monitoring"])
```

### 7. `nix_deployer.py` - NixOS Deployment

**Purpose**: Stage NixOS flakes with tenant-specific configuration and deploy remotely.

**Exported Functions**:

```python
def service_id_to_module_filename(service_id: str) -> str
"""Map service ID to Nix module filename"""

def stage_nix_solution_for_tenant(tenant_name: str) -> Path
"""Create staged nix-solution with selected services"""

def install_nixos_flake_via_ssh(
    vm_name: str,
    ssh_user: str,
    local_nix_dir: Optional[Path] = None
) -> None
"""Copy and install NixOS flake on remote host"""
```

**Dependencies**: `constants`, `utils`, `remote_executor`

**Configuration Requirements**:
- `management-system/nix-solution/` directory structure
- Service modules in `nix-solution/modules/services/`
- Tenant selection.yml with enabled services

**Usage Example**:
```python
from scripts.modules import nix_deployer

staged = nix_deployer.stage_nix_solution_for_tenant("test-tenant")
nix_deployer.install_nixos_flake_via_ssh("test-vm", "admin", staged)
```

### 8. `traefik_config.py` - Traefik Configuration

**Purpose**: Generate dynamic Traefik routing configuration and manage restarts.

**Exported Functions**:

```python
def generate_traefik_dynamic_config(
    general_config: Dict,
    selection_config: Dict
) -> Path
"""Generate Traefik dynamic configuration"""

def restart_traefik() -> None
"""Restart Traefik container"""
```

**Dependencies**: `constants`, `utils`

**Configuration Requirements**:
- Traefik container running
- Dynamic config directory writable

**Usage Example**:
```python
from scripts.modules import traefik_config

traefik_config.generate_traefik_dynamic_config(general, selection)
traefik_config.restart_traefik()
```

## Usage

### Basic Deployment

Deploy a tenant using the default Docker runtime:

```bash
python global-run.py test-tenant
```

### Debug Mode

Enable verbose output with real-time subprocess streaming:

```bash
python global-run.py test-tenant --debug
```

### Command-Line Interface

```
usage: global-run.py [-h] [--debug] tenant

Full-stack orchestrator for Proxmox and Docker services.

positional arguments:
  tenant      The name of the tenant configuration to use (e.g., 'test')

optional arguments:
  -h, --help  show this help message and exit
  --debug     Enable verbose debug output and real-time subprocess logs
```

## Configuration

### Directory Structure

```
thesis-szakdoga/
├── global-run.py              # Main orchestrator script
├── scripts/
│   ├── modules/               # Modular components
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── utils.py
│   │   ├── config_manager.py
│   │   ├── proxmox_provisioner.py
│   │   ├── remote_executor.py
│   │   ├── docker_deployer.py
│   │   ├── nix_deployer.py
│   │   └── traefik_config.py
│   └── README.md              # This file
├── ms-config/
│   └── tenants/
│       └── <tenant-name>/
│           ├── general.conf.yml
│           └── selection.yml
├── management-system/
│   ├── OS_install/
│   │   ├── provision.py
│   │   └── configs/
│   ├── docker-compose-solution/
│   │   ├── docker-compose.yml
│   │   └── traefik/dynamic/
│   ├── nix-solution/
│   │   ├── flake.nix
│   │   ├── install.sh
│   │   └── modules/services/
│   └── website/
│       └── services.json
└── proxmox_api.txt            # Optional: Proxmox API token
```

### Required Environment Variables

- `PROXMOX_VE_API_TOKEN` (optional if proxmox_api.txt exists): Proxmox API token

### Tenant Configuration Files

#### `general.conf.yml`

```yaml
deployment_target: test-vm
deployment_runtime: docker  # or "nix"
tenant_domain: example.com
timezone: America/New_York
universal_username: admin
```

#### `selection.yml`

```yaml
services:
  vaultwarden:
    enabled: true
    options:
      VAULTWARDEN_ADMIN_TOKEN: "your-token"
  jellyfin:
    enabled: true
    options:
      JELLYFIN_PORT: 8096
```

## Deployment Flows

### Docker Deployment Flow

```
1. Configuration Validation
   ├─ Check general.conf.yml
   ├─ Check selection.yml
   ├─ Check services.json
   └─ Verify docker-compose.yml exists

2. VM Provisioning
   ├─ Load Proxmox API token
   ├─ Call provision.py
   └─ Wait for SSH availability

3. Docker Service Deployment
   ├─ Load service definitions
   ├─ Generate .env file
   ├─ Deploy core services (Traefik, Vaultwarden, etc.)
   └─ Wait for initialization

4. Configuration & Restart
   ├─ Generate Traefik dynamic config
   ├─ Generate Homepage dashboard config
   └─ Restart Traefik
```

### NixOS Deployment Flow

```
1. Configuration Validation
   ├─ Check general.conf.yml
   ├─ Check selection.yml
   └─ Verify nix-solution/install.sh exists

2. VM Provisioning
   ├─ Load Proxmox API token
   ├─ Call provision.py
   └─ Wait for SSH availability

3. Flake Staging
   ├─ Load tenant selection
   ├─ Copy base nix-solution structure
   ├─ Copy only enabled service modules
   ├─ Generate flake.nix with tenant defaults
   └─ Embed network configuration

4. Remote Installation
   ├─ Clean remote nix-solution directory
   ├─ SCP staged directory to remote
   ├─ Execute install.sh via Mosh/SSH
   └─ Apply NixOS configuration
```

## Development

### Adding a New Module

1. Create module file in `scripts/modules/`
2. Add module to `__init__.py` imports
3. Import required dependencies
4. Follow existing patterns for error handling
5. Add comprehensive docstrings
6. Update this README with module documentation

### Extending Functionality

**Add a new service runtime:**
1. Create new deployer module (e.g., `kubernetes_deployer.py`)
2. Update `config_manager.lint_configurations()` to check runtime-specific files
3. Add runtime handling in `global-run.py` main flow
4. Document in README

**Add new configuration validation:**
1. Update `config_manager.lint_configurations()`
2. Add validation logic with clear error messages
3. Test with missing/malformed configs

**Add new Proxmox features:**
1. Update `OS_install/provision.py` with new functionality
2. Modify `proxmox_provisioner.provision_proxmox_vm()` if needed
3. Update constants if new paths are required

### Code Style Guidelines

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Write docstrings in Google/NumPy style
- Keep functions focused on single responsibility
- Use constants instead of magic values
- Handle errors gracefully with clear messages
- Add emojis to user-facing output for clarity

### Testing

Test the refactored modules:

```bash
# Dry run with debug mode
python global-run.py test-tenant --debug

# Test specific imports
python -c "from scripts.modules import utils; print(utils.ROOT_DIR)"

# Validate configuration
python -c "from scripts.modules import config_manager; config_manager.lint_configurations('test-tenant')"
```

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'scripts'`

**Solution**: Ensure you're running from the repository root:
```bash
cd /path/to/thesis-szakdoga
python global-run.py tenant-name
```

### Proxmox API Token Issues

**Problem**: `❌ Proxmox API token not found`

**Solution**: Set environment variable or create token file:
```bash
export PROXMOX_VE_API_TOKEN="user@realm!tokenid=secret"
# OR
echo 'PROXMOX_VE_API_TOKEN="user@realm!tokenid=secret"' > proxmox_api.txt
```

### SSH Connection Timeout

**Problem**: `❌ Timed out waiting for SSH`

**Solution**:
- Verify VM is running: Check Proxmox web UI
- Check network connectivity: `ping <vm-ip>`
- Verify SSH keys are configured in `install_config.yaml`
- Check firewall rules allow SSH (port 22)

### Docker Compose Errors

**Problem**: `docker-compose: command not found`

**Solution**: Install Docker Compose or use `docker compose` (v2):
```bash
# Option 1: Install docker-compose v1
pip install docker-compose

# Option 2: Use docker compose v2 (update utils.py if needed)
```

### Traefik Not Restarting

**Problem**: `❌ Error: No such container: traefik`

**Solution**: Verify Traefik was deployed:
```bash
docker ps | grep traefik
docker-compose -f management-system/docker-compose-solution/docker-compose.yml ps
```

### Missing NixOS Service Modules

**Problem**: `⚠️ Missing module files for enabled services (skipped): someservice`

**Solution**:
- Check if module exists: `ls management-system/nix-solution/modules/services/`
- Add module file or disable service in `selection.yml`
- Update `SERVICE_MODULE_MAPPINGS` in `constants.py` if naming differs

### Configuration Validation Failures

**Problem**: `❌ Validation failed with the following errors`

**Solution**: Check the specific error messages and:
- Verify all required YAML files exist
- Ensure YAML syntax is valid: `python -c "import yaml; yaml.safe_load(open('file.yml'))"`
- Check file permissions are readable
- Verify `deployment_target` is set in `general.conf.yml`

## API Reference

### Key Function Signatures

```python
# Configuration Management
config_manager.lint_configurations(tenant_name: str) -> str
config_manager.load_tenant_config(tenant_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]
config_manager.generate_dotenv(general_config: Dict, selection_config: Dict, services_def: Dict) -> Path

# Proxmox Provisioning
proxmox_provisioner.provision_proxmox_vm(vm_name: str, username: str) -> None

# Remote Execution
remote_executor.run_remote_prefer_mosh(remote: str, remote_cmd: str) -> subprocess.CompletedProcess

# Docker Deployment
docker_deployer.deploy_services(profiles: List[str], wait_time: int = 0) -> None

# NixOS Deployment
nix_deployer.stage_nix_solution_for_tenant(tenant_name: str) -> Path
nix_deployer.install_nixos_flake_via_ssh(vm_name: str, ssh_user: str, local_nix_dir: Optional[Path] = None) -> None

# Traefik Configuration
traefik_config.generate_traefik_dynamic_config(general_config: Dict, selection_config: Dict) -> Path
traefik_config.restart_traefik() -> None

# Utilities
utils.run_command(command: list[str], cwd: Path, env: Optional[dict] = None, check: bool = True) -> subprocess.CompletedProcess
utils.wait_for_ssh(host: str, user: str, timeout_sec: int = 600, interval_sec: int = 10) -> bool
utils.get_vm_connection_info(vm_name: str) -> tuple[str, dict]
```

## Module Dependency Graph

```
constants (no dependencies)
    ↓
utils (depends on: constants)
    ↓
├─ config_manager (depends on: constants, utils)
├─ proxmox_provisioner (depends on: constants, utils)
├─ remote_executor (depends on: constants, utils)
│       ↓
├─ docker_deployer (depends on: constants, utils)
├─ nix_deployer (depends on: constants, utils, remote_executor)
└─ traefik_config (depends on: constants, utils)
    ↓
global-run.py (depends on: all modules)
```

## Performance Considerations

- **Debug Mode**: Real-time streaming adds overhead; use only when needed
- **SSH Waits**: Default 600s timeout; adjust `SSH_WAIT_TIMEOUT` in constants.py if needed
- **Service Initialization**: Core services wait 30s by default; increase `CORE_SERVICES_WAIT_TIME` for slower systems
- **Mosh vs SSH**: Mosh provides better performance for long-running commands but requires mosh-server on remote

## Security Best Practices

1. **Never commit secrets**: Add to .gitignore:
   - proxmox_api.txt
   - .env files
   - SSH private keys

2. **Use environment variables** for sensitive data when possible

3. **Restrict file permissions**:
   ```bash
   chmod 600 proxmox_api.txt
   chmod 600 ~/.ssh/id_rsa
   ```

4. **Rotate credentials regularly**: Update Proxmox API tokens and service passwords

5. **Use SSH keys**: Configure in `install_config.yaml` instead of password auth

## Contributing

When modifying the orchestration system:

1. Maintain backward compatibility with existing tenant configs
2. Add comprehensive error handling and validation
3. Update module docstrings and this README
4. Test with both Docker and NixOS runtimes
5. Preserve the CLI interface (or document breaking changes)
6. Add type hints to all new functions
7. Follow existing code style and patterns

## License

This is a thesis project. License to be determined by the thesis author.

## Contact

For questions or issues, contact the thesis project maintainer.
