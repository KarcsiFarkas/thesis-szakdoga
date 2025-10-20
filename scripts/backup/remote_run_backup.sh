#!/usr/bin/env bash
set -euo pipefail

# --- Configuration (I will populate these securely) ---
export RESTIC_PASSWORD="YOUR_RESTIC_REPO_PASSWORD"
export RESTIC_REPOSITORY="/srv/backups/restic-repo"
MAIN_SERVER_HOST="main-server"
MAIN_SERVER_USER="backup-user"
LOG_FILE="/var/log/restic_backup.log"

# --- Script ---
exec > >(tee -a "$LOG_FILE") 2>&1

echo "--- Starting Restic backup at $(date) ---"

# Define backup targets from the main server
BACKUP_TARGETS=(
    "$MAIN_SERVER_USER@$MAIN_SERVER_HOST:/var/lib/vz/dump" # Proxmox VM Backups
    "$MAIN_SERVER_USER@$MAIN_SERVER_HOST:/srv/data/alice/photos"
    "$MAIN_SERVER_USER@$MAIN_SERVER_HOST:/srv/data/alice/documents"
)

restic backup "${BACKUP_TARGETS[@]}"

echo "--- Applying retention policy ---"
restic forget \
    --keep-last 3 \
    --keep-weekly 4 \
    --keep-monthly 6 \
    --keep-yearly 2 \
    --prune

echo "--- Verifying repository integrity ---"
restic check

SPACE_LEFT=$(df -h "$(dirname "$RESTIC_REPOSITORY")" | awk 'NR==2 {print $4}')
echo "Backup complete. Space left: $SPACE_LEFT"

echo "--- Backup process finished. Shutting down. ---"
sudo shutdown now