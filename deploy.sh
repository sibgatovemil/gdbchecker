#!/bin/bash
# Deployment script for GDBChecker

set -e

echo "============================================"
echo "GDBChecker Deployment Script"
echo "============================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo ""
echo "Step 1: Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Update package list
    apt-get update

    # Install prerequisites
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    echo "Docker installed successfully!"
else
    echo "Docker is already installed"
fi

echo ""
echo "Step 2: Setting up project directory..."
PROJECT_DIR="/opt/gdbchecker"

if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    echo "Created directory: $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

echo ""
echo "Step 3: Checking .env file..."
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please create .env file with the following variables:"
    echo "  DB_PASSWORD=your_secure_password"
    echo "  GOOGLE_API_KEY=your_google_api_key"
    echo "  TELEGRAM_BOT_TOKEN=your_telegram_bot_token"
    echo "  TELEGRAM_CHAT_ID=your_telegram_chat_id"
    echo "  CHECK_INTERVAL_HOURS=8"
    exit 1
else
    echo ".env file found"
fi

echo ""
echo "Step 4: Building Docker containers..."
docker compose build

echo ""
echo "Step 5: Starting services..."
docker compose up -d

echo ""
echo "Step 6: Waiting for services to be ready..."
sleep 10

echo ""
echo "Step 7: Checking service status..."
docker compose ps

echo ""
echo "============================================"
echo "Deployment completed!"
echo "============================================"
echo ""
echo "Access the web interface at: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Useful commands:"
echo "  View logs:        docker compose logs -f"
echo "  Restart services: docker compose restart"
echo "  Stop services:    docker compose down"
echo "  Update code:      git pull && docker compose up -d --build"
echo ""
