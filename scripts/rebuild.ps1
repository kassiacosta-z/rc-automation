# PowerShell script para rebuild do Docker
Write-Host "🔄 Rebuilding Docker containers with latest changes..." -ForegroundColor Cyan

# Parar containers existentes
Write-Host "⏹️ Stopping existing containers..." -ForegroundColor Yellow
docker compose down

# Remover imagens antigas
Write-Host "🗑️ Removing old images..." -ForegroundColor Yellow
docker image rm recibos-automation 2>$null

# Build da nova imagem
Write-Host "🔨 Building new image..." -ForegroundColor Yellow
docker compose build --no-cache

# Iniciar containers
Write-Host "🚀 Starting containers..." -ForegroundColor Yellow
docker compose up -d

# Verificar status
Write-Host "📊 Container status:" -ForegroundColor Green
docker compose ps

Write-Host "✅ Rebuild completed! Access at http://localhost:5000" -ForegroundColor Green
