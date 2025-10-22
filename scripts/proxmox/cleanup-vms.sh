#!/usr/bin/env bash
set -euo pipefail

# Cleanup test VMs from Proxmox
# Run this on Proxmox host to clean up failed/test deployments

echo "🧹 Proxmox VM Cleanup Script"
echo "=============================="
echo ""

# List all non-template VMs tagged with 'terraform' or 'paas'
echo "📋 Finding VMs to clean up..."
VMS=$(qm list | grep -E 'terraform|paas|test' | awk '{print $1}' || true)

if [ -z "$VMS" ]; then
    echo "✅ No test VMs found. Nothing to clean up."
    exit 0
fi

echo "Found the following VMs:"
qm list | grep -E 'terraform|paas|test' || true
echo ""

read -p "⚠️  Delete these VMs? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

for VMID in $VMS; do
    echo "🗑️  Deleting VM $VMID..."
    qm stop $VMID --skiplock || true
    sleep 2
    qm destroy $VMID --purge --destroy-unreferenced-disks 1 || true
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Current VMs:"
qm list