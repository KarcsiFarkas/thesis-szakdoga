# Documentation: The `ms-chezmoi` Deployment System

## 1. High-Level Overview

The `ms-chezmoi` folder is the heart of the declarative, template-driven deployment system for the PaaS infrastructure. Its primary responsibility is to **manage and generate the configuration files** required to run the suite of Dockerized services for a specific tenant.

It uses **Chezmoi**, a popular dotfile manager, in a powerful way: as a templating engine. Instead of managing personal dotfiles, it manages the configuration files for an entire server environment. This approach allows for a single set of template files to generate unique, tenant-specific configurations, ensuring deployments are **reproducible, consistent, and easily customizable**.

**Core Principles:**
*   **Declarative:** The templates declare the *desired state* of the system.
*   **Idempotent:** Running the deployment process multiple times will result in the same state, without causing errors.
*   **Tenant-Based:** Each deployment is customized for a specific tenant using variables (e.g., domain names, enabled services).
*   **Version-Controlled:** The entire infrastructure configuration is stored in Git, enabling change tracking, rollbacks, and collaboration.

---

## 2. The General Flow

The `ms-chezmoi` folder is not executed directly. Instead, it is used by the main orchestrator script (`global-run.py`) as part of a larger deployment process.

Here is the step-by-step flow:

1.  **Initiation:** A user runs `global-run.py --tenant <tenant_name>`.
2.  **Configuration Loading:** The orchestrator loads all configuration files for the specified tenant from the `ms-config/tenants/<tenant_name>` directory. This includes which services to enable, domain names, and other settings.
3.  **Chezmoi Execution:** The `chezmoi_deployer` module within the orchestrator executes Chezmoi. It points Chezmoi to the `ms-chezmoi` directory as the "source" and passes the loaded tenant configuration as variables.
4.  **Templating:** Chezmoi processes the `.tmpl` files within `ms-chezmoi/opt/docker/unified/`. It replaces all template variables (e.g., `{{ .tenant.domain }}`) with the actual values for the specified tenant. The output is a complete, ready-to-use set of configuration files, including `docker-compose.yml`.
5.  **Secure Transfer:** The generated files are securely copied (via SSH) to a temporary directory on the target virtual machine (VM).
6.  **Volume Preparation:** On the VM, the `prepare-docker-volumes.sh` script is executed. This script creates the necessary directory structure on the host for Docker's bind mounts, ensuring the correct permissions and ownership are set for each service.
7.  **Service Deployment:** The `docker compose up -d` command is executed on the VM using the generated `docker-compose.yml` file. Docker then pulls the required images and starts all the defined services.
8.  **Validation:** After deployment, the `validate-docker-deployment.sh` script is run to check the health and status of the running containers, ensuring the deployment was successful.

---

## 3. Directory Structure

The structure of `ms-chezmoi` is designed to separate different deployment strategies and their associated files.

```
ms-chezmoi/
└── opt/
    └── docker/
        ├── unified/  <-- The primary, recommended configuration
        │   ├── configs/
        │   │   └── ... (Static config files can go here)
        │   ├── scripts/
        │   │   ├── prepare-docker-volumes.sh  <-- Pre-deployment setup script
        │   │   └── validate-docker-deployment.sh <-- Post-deployment validation script
        │   └── docker-compose.yml.tmpl  <-- The master template for all services
        │
        ├── minimal/     <-- (Optional) A minimal setup for testing
        └── production/  <-- (Optional) A hardened production setup
```

---

## 4. Detailed Script Breakdown

### `scripts/prepare-docker-volumes.sh`

This is a critical pre-deployment script that runs on the target VM.

*   **Purpose:** To create and set permissions for all the directories on the host that will be used as Docker bind mounts. This ensures that the containers have a place to store their persistent data and that they have the correct permissions to write to these directories.

*   **How it Works:**
    1.  It defines a comprehensive list of all directories required by the services in `docker-compose.yml.tmpl`.
    2.  For each directory, it specifies the required **owner**, **group**, and **file permissions**.
    3.  It loops through this list and, for each entry, it:
        *   Creates the directory if it doesn't exist (`sudo mkdir -p`).
        *   Sets the ownership (`sudo chown`).
        *   Sets the file permissions (`sudo chmod`).
    4.  The script is **idempotent**: if a directory already exists with the correct settings, it does nothing.

*   **Key Fix Implemented:** The Nextcloud container runs internally as the `www-data` user (UID `33`). This script specifically sets the ownership of the Nextcloud data directories to `33:33`. This was the fix for the "Cannot create or write into the data directory" error.

*   **Flags and Options:**
    *   `--data-dir DIR`: Overrides the default root directory for Docker data (default: `/opt/docker-data`).
    *   `--user USER`: Sets a default user for ownership (not recommended for Nextcloud).
    *   `--group GROUP`: Sets a default group for ownership.
    *   `--dry-run`: Shows what commands would be run without making any actual changes.
    *   `--verbose`: Enables detailed debug output.
    *   `--help`: Displays the help message.

### `scripts/validate-docker-deployment.sh`

This script runs after `docker compose up` to verify the deployment.

*   **Purpose:** To automatically check if all the deployed services are running and healthy.

*   **How it Works (Inferred):**
    1.  It likely parses the `docker-compose.yml` file to get a list of all defined services.
    2.  It then iterates through each service and uses `docker inspect` to check its state.
    3.  It looks for a status of `running` and, if a healthcheck is defined, a health status of `healthy`.
    4.  It reports any containers that are not running or are unhealthy, providing a quick way to diagnose deployment failures.

---

## 5. Configuration and Templating

### `docker-compose.yml.tmpl`

This is the most important file in the system. It is a **template**, not a standard YAML file.

*   **Purpose:** It serves as the master blueprint for the entire Docker environment. Chezmoi uses this template to generate the final `docker-compose.yml` file.

*   **Templating Syntax:** It uses Go's template syntax.
    *   **Variables:** `{{ .tenant.domain }}` is replaced with the tenant's domain name.
    *   **Conditionals:** `{{- if .services.nextcloud.enabled }}` ... `{{- end }}` blocks allow for entire services to be included or excluded based on the tenant's configuration. This is extremely powerful for creating customized deployments.

### Variables and Options

The variables used in the templates (`{{ .variable }}`) are **not set inside `ms-chezmoi`**. They are passed in by the `global-run.py` orchestrator.

*   **Source of Truth:** The values for these variables come from the YAML configuration files located in:
    `ms-config/tenants/<tenant_name>/`

*   **Required Variables (Examples):**
    *   `tenant.name`: The name of the tenant (e.g., "test").
    *   `tenant.domain`: The primary domain for the tenant (e.g., "example.com").
    *   `deployment.timezone`: The timezone for the services (e.g., "UTC").
    *   `services.<service_name>.enabled`: A boolean (`true` or `false`) that determines if a service is included in the deployment.
    *   `services.traefik.acme_email`: The email address for Let's Encrypt SSL certificate registration.

*   **Secrets and Environment Variables:**
    The `docker-compose.yml.tmpl` file references environment variables like `${AUTHENTIK_DB_PASSWORD}`. These are **not** part of the template variables for security reasons. They are injected at runtime by Docker Compose from a `.env` file, which is also generated by the configuration management system based on the tenant's credential settings.
