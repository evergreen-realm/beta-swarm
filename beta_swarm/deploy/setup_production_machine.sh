#!/bin/bash
set -e

echo "Setting up Production Machine for Beta Swarm v3.1..."

# 1. Start Support Services
echo "Starting Bugsink..."
docker-compose -f bugsink-docker-compose.yml up -d

echo "Starting Monitoring Stack..."
docker-compose -f monitoring-docker-compose.yml up -d

echo "Starting Letta & Cognee (Brain Layers)..."
docker-compose -f letta-docker-compose.yml up -d
docker-compose -f cognee-docker-compose.yml up -d

# 2. Wait for services to initialize
echo "Waiting for support services to initialize..."
sleep 15

# 3. Start Core Swarm
echo "Starting Core Swarm..."
./master_setup.sh

echo "Production Environment is fully operational!"
