#!/usr/bin/env bash
set -euo pipefail

# Prepare Ubuntu Cloud Template for Proxmox
# Run this script on your Proxmox host to create/update VM template 9000
# Usage: bash prepare-ubuntu-template.sh

TEMPLATE_ID=9000
TEMPLATE_NAME="ubuntu-2404-cloud-template"
NODE_NAME="fkarcsi"  # Change to your node name
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
    --scsihw virtio-scsi-pci

# Import disk
echo "💾 Importing disk..."
qm importdisk ${TEMPLATE_ID} "${CLOUD_IMAGE}" "${STORAGE}"

# Attach disk
echo "🔗 Attaching disk..."
qm set ${TEMPLATE_ID} \
    --scsi0 "${STORAGE}:vm-${TEMPLATE_ID}-disk-0" \
    --boot c \
    --bootdisk scsi0

# Add cloud-init drive
echo "☁️  Adding cloud-init drive..."
qm set ${TEMPLATE_ID} --ide2 "${STORAGE}:cloudinit"

# Configure cloud-init defaults
echo "⚙️  Configuring cloud-init..."
qm set ${TEMPLATE_ID} \
    --ciuser ubuntu \
    --cipassword "$(openssl rand -base64 12)" \
    --ipconfig0 ip=dhcp \
    --nameserver "1.1.1.1 8.8.8.8" \
    --searchdomain "local"

# Add serial console for cloud-init output
qm set ${TEMPLATE_ID} --serial0 socket --vga serial0

# Enable QEMU guest agent
qm set ${TEMPLATE_ID} --agent enabled=1,fstrim_cloned_disks=1

# Resize disk to 10GB (will be resized by Terraform later)
qm resize ${TEMPLATE_ID} scsi0 10G

# Important: Start VM once to pre-install qemu-guest-agent
echo "🔄 Starting VM to install QEMU guest agent..."
qm start ${TEMPLATE_ID}

echo "⏳ Waiting 60 seconds for cloud-init to complete..."
sleep 60

# Install qemu-guest-agent
echo "📦 Installing QEMU guest agent..."
ssh -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=30 \
    ubuntu@$(qm guest cmd ${TEMPLATE_ID} network-get-interfaces | jq -r '.[1].["ip-addresses"][0]["ip-address"]' 2>/dev/null || echo "dhcp") \
    'sudo apt-get update && sudo apt-get install -y qemu-guest-agent && sudo systemctl enable qemu-guest-agent && sudo systemctl start qemu-guest-agent' \
    || echo "⚠️  Manual agent installation may be needed"

# Clean up the VM
echo "🧹 Cleaning up VM..."
ssh -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    ubuntu@$(qm guest cmd ${TEMPLATE_ID} network-get-interfaces | jq -r '.[1].["ip-addresses"][0]["ip-address"]' 2>/dev/null || echo "dhcp") \
    'sudo cloud-init clean && sudo apt-get clean && sudo sync' \
    || true

# Stop VM
echo "🛑 Stopping VM..."
qm stop ${TEMPLATE_ID}
sleep 5

# Convert to template
echo "📋 Converting to template..."
qm template ${TEMPLATE_ID}

echo ""
echo "✅ Template ${TEMPLATE_ID} (${TEMPLATE_NAME}) created successfully!"
echo ""
echo "Template details:"
qm config ${TEMPLATE_ID}
echo ""
echo "🎉 You can now use this template with Terraform!"
echo "   Clone VM ID: ${TEMPLATE_ID}"