#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME=${IMAGE_NAME:-recibos-automation}

echo "Construindo imagem ${IMAGE_NAME}..."
docker build -t ${IMAGE_NAME} .
echo "OK"
