#!/usr/bin/env bash
set -euo pipefail

# Assumes LLDAP is running in a container named 'lldap'.
# Reads variables.nix from the tenant's general.conf file.

if [[ -z "${ADMIN_USER:-}" || -z "${GLOBAL_PASSWORD:-}" ]]; then
    echo "Error: ADMIN_USER and GLOBAL_PASSWORD must be set in the environment." >&2
    exit 1
fi

LLDAP_CONTAINER_NAME="lldap" # This should be parameterized if needed

echo "--- Provisioning initial LLDAP admin user ---"
echo "Waiting for LLDAP container to be healthy..."
until docker container inspect -f '{{.State.Health.Status}}' "$LLDAP_CONTAINER_NAME" 2>/dev/null | grep -q "healthy"; do
    echo -n "."
    sleep 2
done
echo " LLDAP is ready."

echo "Creating user '$ADMIN_USER'..."
docker exec "$LLDAP_CONTAINER_NAME" /usr/local/bin/lldap user new \
    --user-name "$ADMIN_USER" \
    --password "$GLOBAL_PASSWORD" \
    --display-name "Admin User" || echo "User '$ADMIN_USER' may already exist. Continuing."

echo "--- LLDAP provisioning complete. ---"