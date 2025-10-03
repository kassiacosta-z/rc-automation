# syntax=docker/dockerfile:1

# ===== Stage 1: builder =====
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primeiro para cache
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ===== Stage 2: runtime =====
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Usuário não-root
RUN useradd -m appuser

# Dependências mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar wheels e instalar
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copiar código
COPY . /app

# Criar diretórios de dados/logs com permissões
RUN mkdir -p /app/data /app/logs /app/credentials /app/tokens && \
    chown -R appuser:appuser /app

# Expor porta
EXPOSE 5000

# Healthcheck simples chamando /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Alternar para usuário não-root
USER appuser

# Comando de execução
CMD ["python", "app.py"]