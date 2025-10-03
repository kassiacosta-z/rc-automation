# -*- coding: utf-8 -*-
# Dockerfile para versão refatorada com Design Patterns
# Multi-stage build otimizado para produção

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

# Metadados da imagem
LABEL maintainer="Zello Tecnologia <contato@zello.tec.br>"
LABEL description="Sistema de Automação de Recibos de IA - Versão Refatorada"
LABEL version="2.0.0"

# Instalar dependências do sistema para build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

# Instalar dependências de runtime
RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    poppler-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Definir diretório de trabalho
WORKDIR /app

# Copiar dependências Python do stage anterior
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p data logs uploads tokens credentials static && \
    chown -R appuser:appuser /app

# Definir permissões
RUN chmod +x scripts/*.sh 2>/dev/null || true

# Mudar para usuário não-root
USER appuser

# Adicionar diretório local ao PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Variáveis de ambiente
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expor porta
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Comando de inicialização
CMD ["python", "app.py"]
