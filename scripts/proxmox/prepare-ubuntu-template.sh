#!/usr/bin/env bash
set -euo pipefail

# Prepare Ubuntu Cloud Template for Proxmox
# This version creates a MINIMAL template that Terraform can customize

TEMPLATE_ID=9000
TEMPLATE_NAME="ubuntu-2404-cloud-template"
NODE_NAME="fkarcsi"
STORAGE="local-lvm"
UBUNTU_VERSION="24.04"

echo "🚀 Creating Ubuntu ${UBUNTU_VERSION} cloud template (VM ID: ${TEMPLATE_ID})"

# Check if template already exists
if qm status ${TEMPLATE_ID} >/dev/null 2>&1; then
    echo "⚠️  VM ${TEMPLATE_ID} already exists. Destroying it..."
    qm stop ${TEMPLATE_ID} || true
    sleep 2
    qm destroy ${TEMPLATE_ID} --purge
fi

# Download Ubuntu cloud image
CLOUD_IMAGE="noble-server-cloudimg-amd64.img"
IMAGE_URL="https://cloud-images.ubuntu.com/noble/current/${CLOUD_IMAGE}"

echo "📥 Downloading Ubuntu cloud image..."
cd /tmp
if [ ! -f "${CLOUD_IMAGE}" ]; then
    wget -q --show-progress "${IMAGE_URL}" || {
        echo "❌ Failed to download cloud image"
        exit 1
    }
else
    echo "✅ Cloud image already downloaded"
fi

# Create VM
echo "🔧 Creating VM ${TEMPLATE_ID}..."
qm create ${TEMPLATE_ID} \
    --name "${TEMPLATE_NAME}" \
    --memory 2048 \
    --cores 2 \
    --net0 virtio,bridge=vmbr0 \
    --scsihw virtio-scsi-single

# Import disk
echo "💾 Importing disk..."
qm set ${TEMPLATE_ID} --scsi0 "${STORAGE}:0,import-from=/tmp/${CLOUD_IMAGE}"

# Set boot order
echo "🥾 Configuring boot..."
qm set ${TEMPLATE_ID} --boot order=scsi0

# Add cloud-init drive (IDE instead of SCSI for better compatibility)
echo "☁️  Adding cloud-init drive..."
qm set ${TEMPLATE_ID} --ide2 "${STORAGE}:cloudinit"

# Enable QEMU guest agent
echo "🤖 Enabling QEMU agent..."
qm set ${TEMPLATE_ID} --agent enabled=1,fstrim_cloned_disks=1

# Add serial console for cloud-init output
echo "📺 Adding serial console..."
qm set ${TEMPLATE_ID} --serial0 socket --vga serial0

# ⚠️ IMPORTANT: Do NOT set cloud-init defaults here
# Let Terraform configure them via user_data_file_id
echo "⚙️  Skipping cloud-init defaults (Terraform will configure)"

# Resize disk to 10GB base (Terraform will resize further)
echo "💿 Resizing disk..."
qm disk resize ${TEMPLATE_ID} scsi0 10G

# Convert to template immediately (don't start it)
echo "📋 Converting to template..."
qm template ${TEMPLATE_ID}

echo ""
echo "✅ Template ${TEMPLATE_ID} (${TEMPLATE_NAME}) created successfully!"
echo ""
echo "⚠️  IMPORTANT: This is a MINIMAL template."
echo "   All configuration (users, network, packages) will be done by Terraform."
echo ""
echo "Template configuration:"
qm config ${TEMPLATE_ID}
echo ""
echo "🎉 Ready to use with Terraform!"