#!/bin/bash
echo "🔄 Rebuilding Docker containers with latest changes..."

# Parar containers existentes
echo "⏹️ Stopping existing containers..."
docker compose down

# Remover imagens antigas
echo "🗑️ Removing old images..."
docker image rm recibos-automation 2>/dev/null || true

# Build da nova imagem
echo "🔨 Building new image..."
docker compose build --no-cache

# Iniciar containers
echo "🚀 Starting containers..."
docker compose up -d

# Verificar status
echo "📊 Container status:"
docker compose ps

echo "✅ Rebuild completed! Access at http://localhost:5000"
