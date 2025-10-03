#!/usr/bin/env bash
set -euo pipefail

echo "Subindo com docker-compose..."
docker compose up -d --build
echo "Acesse: http://localhost:5001"
