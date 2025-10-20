#!/usr/bin/env bash
set -euo pipefail

# IMPORTANT: BW_CLIENTID, BW_CLIENTSECRET, and BW_PASSWORD must be exported
# as environment variables before running this script.

if [[ -z "${BW_CLIENTID:-}" || -z "${BW_CLIENTSECRET:-}" || -z "${BW_PASSWORD:-}" ]]; then
    echo "Error: BW_CLIENTID, BW_CLIENTSECRET, and BW_PASSWORD must be set." >&2
    exit 1
fi

ADMIN_USER="admin"
VAULTWARDEN_CONTAINER_NAME="vaultwarden"

echo "--- Provisioning service passwords with Vaultwarden ---"
if ! command -v bw &> /dev/null || ! command -v jq &> /dev/null; then
    echo "ERROR: 'bw' (Bitwarden CLI) and 'jq' are required." >&2
    exit 1
fi

echo "Waiting for Vaultwarden container..."
until docker container inspect -f '{{.State.Running}}' "$VAULTWARDEN_CONTAINER_NAME" 2>/dev/null | grep -q "true"; do
    sleep 2; echo -n ".";
done
echo " Vaultwarden is ready."

echo "Authenticating with Bitwarden CLI..."
bw config server "http://$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $VAULTWARDEN_CONTAINER_NAME):80"
bw login --apikey
export BW_SESSION=$(bw unlock --passwordenv BW_PASSWORD --raw)
echo "Authentication successful."

# Source service selections
source "$TENANT_DIR/selection.conf"

# Define services that need passwords
SERVICES_TO_PROVISION=()
if [[ "${SERVICE_NEXTCLOUD_ENABLED:-false}" == "true" ]]; then SERVICES_TO_PROVISION+=("nextcloud"); fi
if [[ "${SERVICE_GITLAB_ENABLED:-false}" == "true" ]]; then SERVICES_TO_PROVISION+=("gitlab"); fi
#... add all other services here

for SERVICE_NAME in "${SERVICES_TO_PROVISION[@]}"; do
    echo "--- Processing $SERVICE_NAME ---"
    
    GENERATED_PASS=$(bw generate --length 32 --special --number --uppercase)
    
    echo "Storing password in Vaultwarden..."
    ITEM_JSON=$(bw get template item | jq \
        --arg name "$SERVICE_NAME" \
        --arg user "$ADMIN_USER" \
        --arg pass "$GENERATED_PASS" \
        '.name = $name | .login.username = $user | .login.password = $pass')
    
    bw create item "$ITEM_JSON" > /dev/null
    
    # Inject password into deployment config (for Docker)
    echo "${SERVICE_NAME^^}_PASSWORD=${GENERATED_PASS}" >> "$PROJECT_ROOT/docker-compose-solution/.env"
    echo "Password for $SERVICE_NAME injected."

    # Verification
    RETRIEVED_PASS=$(bw get password "$SERVICE_NAME")
    if [[ "$RETRIEVED_PASS" == "$GENERATED_PASS" ]]; then
        echo "✅ Verification successful for $SERVICE_NAME."
    else
        echo "❌ ERROR: Password mismatch for $SERVICE_NAME!" >&2
        exit 1
    fi
done

bw logout
unset BW_SESSION
echo "--- All passwords provisioned and verified. ---"