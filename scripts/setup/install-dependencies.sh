#!/usr/bin/env bash
set -euo pipefail

# Install all dependencies for the PaaS orchestration system
# Run this on your orchestration/management machine (not Proxmox host)

echo "🚀 Installing PaaS Orchestration Dependencies"
echo "=============================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ Cannot detect OS. /etc/os-release not found."
    exit 1
fi

echo "📋 Detected OS: $OS"
echo ""

# Install based on OS
case $OS in
    ubuntu|debian)
        echo "📦 Installing dependencies for Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y \
            python3.12 \
            python3.12-venv \
            python3-pip \
            git \
            curl \
            wget \
            jq \
            sshpass \
            wakeonlan

        # Install Ansible
        echo "📦 Installing Ansible..."
        sudo apt-get install -y software-properties-common
        sudo add-apt-repository -y ppa:ansible/ansible
        sudo apt-get update
        sudo apt-get install -y ansible

        # Install Terraform
        echo "📦 Installing Terraform..."
        if ! command -v terraform &> /dev/null; then
            wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
            sudo apt-get update
            sudo apt-get install -y terraform
        else
            echo "✅ Terraform already installed"
        fi
        ;;

    fedora|rhel|centos)
        echo "📦 Installing dependencies for RHEL/Fedora..."
        sudo dnf install -y \
            python3.12 \
            python3-pip \
            git \
            curl \
            wget \
            jq \
            sshpass \
            ansible

        # Install Terraform
        if ! command -v terraform &> /dev/null; then
            sudo dnf install -y dnf-plugins-core
            sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
            sudo dnf install -y terraform
        fi
        ;;

    *)
        echo "❌ Unsupported OS: $OS"
        echo "Please install manually:"
        echo "  - Python 3.12+"
        echo "  - Ansible"
        echo "  - Terraform"
        echo "  - jq, curl, wget, git"
        exit 1
        ;;
esac

# Install Docker Compose
echo "📦 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose already installed"
fi

# Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."
cd "$(dirname "$0")/../.."  # Go to repo root
python3.12 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install pyyaml pydantic ansible-core

echo ""
echo "✅ All dependencies installed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Set up Proxmox API token:"
echo "   echo 'PROXMOX_VE_API_TOKEN=\"user@pve!token=secret\"' > proxmox_api.txt"
echo "   chmod 600 proxmox_api.txt"
echo ""
echo "3. Create Ubuntu template on Proxmox:"
echo "   bash scripts/proxmox/prepare-ubuntu-template.sh"
echo ""
echo "4. Run the orchestrator:"
echo "   .venv/bin/python3.12 global-run.py test"