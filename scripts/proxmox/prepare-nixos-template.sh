#!/usr/bin/env bash
set -euo pipefail
# NixOS Template Preparation for Proxmox
# Creates a minimal NixOS template with Python support for Ansible provisioning
# This script handles the automated portions; manual NixOS installation still required
TEMPLATE_ID="${NIXOS_TEMPLATE_ID:-8000}"
NODE="${PROXMOX_NODE:-pve}"
STORAGE="${PROXMOX_STORAGE:-local-lvm}"
NIXOS_ISO="${NIXOS_ISO:-/var/lib/vz/template/iso/nixos-minimal-25.05.iso}"
TEMPLATE_IP="192.168.1.80"
TEMPLATE_GATEWAY="192.168.1.1"
BRIDGE="${BRIDGE:-vmbr0}"
echo "================================================================"
echo "NixOS Template Preparation for Proxmox"
echo "================================================================"
echo ""
echo "Template ID: ${TEMPLATE_ID}"
echo "Node: ${NODE}"
echo "Storage: ${STORAGE}"
echo "ISO: ${NIXOS_ISO}"
echo "Network Bridge: ${BRIDGE}"
echo ""
read -p "Proceed with template creation? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
# Check if template already exists
if qm status ${TEMPLATE_ID} &>/dev/null; then
    echo "
  VM ${TEMPLATE_ID} already exists!"
  VM ${TEMPLATE_ID} already exists!"
    read -p "Destroy and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if qm status ${TEMPLATE_ID} | grep -q "running"; then
            echo "Stopping VM ${TEMPLATE_ID}..."
            qm stop ${TEMPLATE_ID}
            sleep 5
        fi
        echo "Destroying VM ${TEMPLATE_ID}..."
        qm destroy ${TEMPLATE_ID} --purge
    else
        echo "Aborted."
        exit 1
    fi
echo ""
echo "Creating VM ${TEMPLATE_ID}..."
qm create ${TEMPLATE_ID} \
  --name nixos-template \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=${BRIDGE} \
  --scsihw virtio-scsi-single \
  --scsi0 ${STORAGE}:20 \
  --ide2 ${NIXOS_ISO},media=cdrom \
  --boot order=ide2 \
  --ostype l26 \
  --agent enabled=1 \
  --serial0 socket \
  --vga serial0
echo "
 VM created successfully!"
echo ""
echo "Starting VM for installation..."
qm start ${TEMPLATE_ID}
echo ""
echo "================================================================"
echo "MANUAL INSTALLATION REQUIRED"
echo "================================================================"
echo ""
echo "Connect to VM console:"
echo "  qm terminal ${TEMPLATE_ID}"
echo ""
echo "Or via VNC/web console in Proxmox UI"
echo ""
echo "----------------------------------------------------------------"
echo "Installation Steps:"
echo "----------------------------------------------------------------"
echo ""
echo "1. Wait for NixOS live environment to boot"
echo ""
echo "2. Partition the disk:"
echo "     sudo -i"
echo "     parted /dev/sda -- mklabel msdos"
echo "     parted /dev/sda -- mkpart primary 1MB 100%"
echo "     parted /dev/sda -- set 1 boot on"
echo "     mkfs.ext4 -L nixos /dev/sda1"
echo "     mount /dev/disk/by-label/nixos /mnt"
echo ""
echo "3. Generate initial config:"
echo "     nixos-generate-config --root /mnt"
echo ""
echo "4. Edit /mnt/etc/nixos/configuration.nix with this content:"
echo ""
cat << 'NIXOS_CONFIG'
{ config, lib, pkgs, ... }:
  imports = [
    ./hardware-configuration.nix
    <nixpkgs/nixos/modules/profiles/qemu-guest.nix>
  ];
  # ==========================================
  # Boot & Serial Console
  # ==========================================
  boot.loader.grub.enable = true;
  boot.loader.grub.device = "/dev/sda";
  boot.loader.timeout = 5;
  boot.kernelParams = [ "console=ttyS0,115200" "console=tty1" ];
  boot.loader.grub.extraConfig = ''
    serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1
    terminal_input serial console
    terminal_output serial console
  '';
  # ==========================================
  # Networking
  # ==========================================
  networking.hostName = "nixos-template";
  networking.useNetworkd = true;
  networking.networkmanager.enable = false;
  networking.useDHCP = false;
  # Static IP for template access
  networking.interfaces.eth0.ipv4.addresses = [
    { address = "192.168.1.80"; prefixLength = 24; }
  ];
  networking.defaultGateway = {
    address = "192.168.1.1";
    interface = "eth0";
  };
  networking.nameservers = [ "1.1.1.1" ];
  networking.firewall.allowedTCPPorts = [ 22 ];
  # ==========================================
  # System Services
  # ==========================================
  time.timeZone = "Europe/Amsterdam";
  services.chrony.enable = true;
  # QEMU Guest Agent (for Proxmox integration)
  services.qemuGuest.enable = true;
  # NOTE: Cloud-init is NOT enabled in template
  # Proxmox handles initialization via NoCloud datasource
  # services.cloud-init.enable = false;
  # ==========================================
  # Remote Access
  # ==========================================
  programs.mosh.enable = true;
  services.openssh = {
    enable = true;
    settings.PermitRootLogin = "yes";
  };
  # ==========================================
  # User Management
  # ==========================================
  users.users.root.password = "nixos";
  services.getty.autologinUser = "root";
  # ==========================================
  # Packages - MUST INCLUDE PYTHON3 FOR ANSIBLE
  # ==========================================
  environment.systemPackages = with pkgs; [
    vim wget helix yazi git curl
    htop nettools cacert
    python3  # Required for Ansible provisioning
  ];
  # ==========================================
  # System State
  # ==========================================
  system.stateVersion = "25.05";
NIXOS_CONFIG
echo ""
echo "5. Install NixOS:"
echo "     nixos-install --no-root-passwd"
echo ""
echo "6. Reboot into installed system:"
echo "     reboot"
echo ""
echo "7. After reboot, verify Python is available:"
echo "     ssh root@${TEMPLATE_IP}"
echo "     python3 --version"
echo "     ls -la /run/current-system/sw/bin/python3"
echo ""
echo "8. Clean up for template conversion:"
echo "     rm -rf /root/.bash_history /root/.ssh/known_hosts"
echo "     rm -rf /home/*/.bash_history /home/*/.ssh/known_hosts"
echo "     truncate -s 0 /etc/machine-id"
echo "     shutdown -h now"
echo ""
echo "================================================================"
echo ""
read -p "Press Enter when installation is complete and VM is shut down..."
echo ""
echo "Converting VM to template..."
qm set ${TEMPLATE_ID} --ide2 none
qm template ${TEMPLATE_ID}
echo ""
echo "================================================================"
echo "
 NixOS Template ${TEMPLATE_ID} Created Successfully!"
echo "================================================================"
echo ""
echo "Template Configuration:"
echo "  - ID: ${TEMPLATE_ID}"
echo "  - Name: nixos-template"
echo "  - OS: NixOS 25.05 (Warbler)"
echo "  - Python: Included in system packages"
echo "  - QEMU Guest Agent: Enabled"
echo "  - Cloud-init: Disabled (uses Proxmox NoCloud)"
echo ""
echo "To use this template, configure in configs/defaults.yaml:"
echo ""
echo "  proxmox_provider:"
echo "    nixos_template: \"${TEMPLATE_ID}\""
echo ""
echo "Or set environment variable:"
echo "  export NIXOS_TEMPLATE=${TEMPLATE_ID}"
echo ""
echo "Test provisioning with:"
echo "  cd management-system/OS_install"
echo "  python3 provision.py --hosts <hostname> --debug"
echo ""
