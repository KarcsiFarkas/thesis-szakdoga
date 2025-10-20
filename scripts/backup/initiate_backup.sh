#!/usr/bin/env bash
set -euo pipefail

# --- Configuration (I will replace these values) ---
BACKUP_SERVER_MAC="00:11:22:33:44:55"
BACKUP_SERVER_HOST="backup-server" # SSH host alias for the backup PC
BACKUP_SERVER_USER="backup"
MAIN_SERVER_HOST="main-server"     # SSH host alias for this server
MAIN_SERVER_USER="admin"
READY_SIGNAL_FILE="/tmp/backup_server_ready"
TIMEOUT_MINS=5

# --- Script ---
echo "Starting backup process at $(date)"
# Clean up any stale signal files first
ssh "$MAIN_SERVER_USER@$MAIN_SERVER_HOST" "rm -f $READY_SIGNAL_FILE"

# 1. Wake the backup server
python3 "$(dirname "$0")/wake_on_lan.py" "$BACKUP_SERVER_MAC"

# 2. Wait for the ready signal
echo "Waiting for ready signal... (timeout: ${TIMEOUT_MINS}m)"
for i in $(seq 1 $((TIMEOUT_MINS * 12))); do
    if ssh "$MAIN_SERVER_USER@$MAIN_SERVER_HOST" "test -f $READY_SIGNAL_FILE"; then
        echo "Ready signal received."
        
        # 3. Trigger the backup on the remote server
        echo "Triggering remote backup script on $BACKUP_SERVER_HOST..."
        ssh "$BACKUP_SERVER_USER@$BACKUP_SERVER_HOST" "/opt/backup/remote_run_backup.sh"
        
        # 4. Clean up and exit
        ssh "$MAIN_SERVER_USER@$MAIN_SERVER_HOST" "rm -f $READY_SIGNAL_FILE"
        echo "Backup process finished successfully."
        exit 0
    fi
    sleep 5
done

echo "ERROR: Timed out after $TIMEOUT_MINS minutes waiting for backup server." >&2
exit 1