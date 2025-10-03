#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=${1:-backup_$(date +%Y%m%d_%H%M%S)}
mkdir -p ${BACKUP_DIR}

cp -a data ${BACKUP_DIR}/data
cp -a logs ${BACKUP_DIR}/logs
cp -a credentials ${BACKUP_DIR}/credentials
cp -a tokens ${BACKUP_DIR}/tokens || true

echo "Backup concluído em ${BACKUP_DIR}" 
