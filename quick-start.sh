#!/bin/bash

# Voting App Quick Start Script
# Bu script loyihani serverda tez ishga tushirish uchun

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
cat << "EOF"
 _    __     __  _               ___
| |  / /____/ /_(_)___  ____ _  /   |  ____  ____
| | / / __ / __/ / __ \/ __ `/ / /| | / __ \/ __ \
| |/ / /_/ / /_/ / / / / /_/ / / ___ |/ /_/ / /_/ /
|___/\____/\__/_/_/ /_/\__, / /_/  |_/ .___/ .___/
                      /____/        /_/   /_/

Quick Start Installation
EOF
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root/sudo${NC}"
    exit 1
fi

# Get server IP
SERVER_IP=$(curl -s ifconfig.me || echo "localhost")
echo -e "${GREEN}Detected Server IP: $SERVER_IP${NC}"
echo ""

# Step 1: Check Docker
echo -e "${YELLOW}Step 1: Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}Docker installed!${NC}"
    echo -e "${YELLOW}Please logout and login again, then run this script again.${NC}"
    exit 0
else
    echo -e "${GREEN}Docker is installed${NC}"
fi

# Step 2: Check Docker Compose
echo -e "${YELLOW}Step 2: Checking Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Installing..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installed!${NC}"
else
    echo -e "${GREEN}Docker Compose is installed${NC}"
fi

# Step 3: Setup Environment Files
echo -e "${YELLOW}Step 3: Setting up environment files...${NC}"

# API .env
if [ ! -f "api/.env" ]; then
    if [ -f "api/.env.example" ]; then
        cp api/.env.example api/.env

        # Generate random secret key
        SECRET_KEY=$(openssl rand -hex 32)

        # Replace placeholders
        sed -i.bak "s|your-very-long-random-secret-key-minimum-32-characters-here|$SECRET_KEY|g" api/.env
        sed -i.bak "s|http://localhost:8000|http://$SERVER_IP:8000|g" api/.env
        sed -i.bak "s|http://localhost:5173|http://$SERVER_IP|g" api/.env

        rm api/.env.bak

        echo -e "${GREEN}Created api/.env${NC}"
        echo -e "${YELLOW}IMPORTANT: Please edit api/.env and change:${NC}"
        echo "  - ADMIN_PASSWORD"
        echo "  - EXTERNAL_API_TOKEN"
    else
        echo -e "${RED}api/.env.example not found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}api/.env already exists${NC}"
fi

# Web .env
if [ ! -f "web/.env" ]; then
    if [ -f "web/.env.example" ]; then
        cp web/.env.example web/.env
        sed -i.bak "s|http://localhost:8000|http://$SERVER_IP:8000|g" web/.env
        rm web/.env.bak
        echo -e "${GREEN}Created web/.env${NC}"
    else
        echo -e "${RED}web/.env.example not found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}web/.env already exists${NC}"
fi

# Step 4: Setup Firewall (UFW)
echo -e "${YELLOW}Step 4: Setting up firewall...${NC}"
if command -v ufw &> /dev/null; then
    echo "Configuring UFW firewall..."

    # Check if UFW is active
    if sudo ufw status | grep -q "Status: active"; then
        echo "UFW is active"
    else
        echo "Enabling UFW..."
        sudo ufw --force enable
    fi

    # Allow ports
    sudo ufw allow 22/tcp comment "SSH"
    sudo ufw allow 80/tcp comment "HTTP"
    sudo ufw allow 8000/tcp comment "API"

    echo -e "${GREEN}Firewall configured${NC}"
else
    echo -e "${YELLOW}UFW not found, skipping firewall setup${NC}"
fi

# Step 5: Create required directories
echo -e "${YELLOW}Step 5: Creating directories...${NC}"
mkdir -p data backups
echo -e "${GREEN}Directories created${NC}"

# Step 6: Build and start containers
echo -e "${YELLOW}Step 6: Building and starting containers...${NC}"
echo "This may take a few minutes..."

if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml up -d --build
else
    docker-compose up -d --build
fi

# Wait for containers to be ready
echo "Waiting for containers to start..."
sleep 10

# Step 7: Initialize database
echo -e "${YELLOW}Step 7: Initializing database...${NC}"
if [ ! -f "data/voting.db" ]; then
    docker exec voting_api python -m app.init_db
    echo -e "${GREEN}Database initialized${NC}"
else
    echo -e "${GREEN}Database already exists${NC}"
fi

# Step 8: Display results
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Access URLs:${NC}"
echo "  Frontend: http://$SERVER_IP"
echo "  API Docs: http://$SERVER_IP:8000/docs"
echo "  Admin Panel: http://$SERVER_IP/admin/login"
echo ""
echo -e "${YELLOW}Default Credentials:${NC}"
echo "  Username: admin"
echo "  Password: (check api/.env file)"
echo ""
echo -e "${RED}IMPORTANT SECURITY STEPS:${NC}"
echo "  1. Edit api/.env and change ADMIN_PASSWORD"
echo "  2. Add your EXTERNAL_API_TOKEN in api/.env"
echo "  3. Restart: docker-compose restart"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:       docker-compose logs -f"
echo "  Stop:            docker-compose down"
echo "  Restart:         docker-compose restart"
echo "  Backup:          ./deploy.sh backup"
echo ""
echo -e "${GREEN}For more details, see DEPLOY.md${NC}"
echo ""

# Make deploy.sh executable
if [ -f "deploy.sh" ]; then
    chmod +x deploy.sh
fi
