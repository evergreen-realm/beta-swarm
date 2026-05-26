#!/bin/bash
set -e

echo "Setting up Beta Swarm Master Environment..."

# Ensure checkpoints and workspace directories exist
mkdir -p ../checkpoints ../workspace ../kuzu_db

# Build and start the master services
docker-compose -f master-docker-compose.yml up -d --build

echo "Master environment running on port 8080 (Core) and 8765 (GitNexus MCP)"
