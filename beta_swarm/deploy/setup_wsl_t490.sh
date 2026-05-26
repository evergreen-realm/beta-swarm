#!/bin/bash
set -e

echo "Setting up Beta Swarm v3.1 on WSL (T490 RAM-Constrained Profile)..."

# Optimize WSL memory
echo "Configuring WSL memory limits..."
if [ ! -f /etc/wsl.conf ]; then
    echo "[wsl2]" | sudo tee /etc/wsl.conf
    echo "memory=12GB" | sudo tee -a /etc/wsl.conf
    echo "swap=16GB" | sudo tee -a /etc/wsl.conf
fi

echo "Starting core services in lightweight mode..."
docker-compose -f letta-docker-compose.yml up -d
docker-compose -f monitoring-docker-compose.yml up -d

echo "WSL T490 Setup complete. Ensure LM Studio and Ollama are running in Windows host."
