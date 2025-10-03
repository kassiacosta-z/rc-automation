"""Models package para automação de recibos de IA (v2.0)"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, ForeignKey, BigInteger, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class JobStatus:
    DISCOVERED = "discovered"
    ENQUEUED = "enqueued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRIED = "retried"


# Importar novos modelos de recibos
from .receipt_models import ReceiptJob, Recibo

# Aliases para compatibilidade
ReceiptData = Recibo

__all__ = [
    "JobStatus",
    "ReceiptJob",
    "Recibo", 
    "ReceiptData",
]