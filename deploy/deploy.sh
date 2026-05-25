#!/bin/bash
set -euo pipefail
echo "Starting Beta Swarm Deployment..."
docker-compose up -d
echo "Deployment successful."
