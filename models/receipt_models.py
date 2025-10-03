"""Modelos para processamento de recibos de IA."""

from __future__ import annotations
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Date, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models import JobStatus


class ReceiptJob(Base):
    """Job de processamento de recibo."""
    __tablename__ = "receipt_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_email_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'EMAIL' ou 'API'
    plataforma: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default=JobStatus.DISCOVERED)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamentos
    # artifacts: Mapped[list["ProcessingArtifact"]] = relationship(
    #     back_populates="receipt_job", cascade="all, delete-orphan"
    # )
    # logs: Mapped[list["ProcessingLog"]] = relationship(
    #     back_populates="receipt_job", cascade="all, delete-orphan"
    # )
    recibo: Mapped[Optional["Recibo"]] = relationship(back_populates="job", uselist=False)


class Recibo(Base):
    """Dados estruturados de um recibo processado."""
    __tablename__ = "recibos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("receipt_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Dados extraídos
    plataforma: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default='BRL')
    data_emissao: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    periodo_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    numero_recibo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tipo_cobranca: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confianca: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Metadados
    fonte_dados: Mapped[str] = mapped_column(String(10), nullable=False)  # 'EMAIL' ou 'API'
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relacionamento
    job: Mapped["ReceiptJob"] = relationship(back_populates="recibo")
    
    # Constraint de unicidade
    __table_args__ = (
        UniqueConstraint('numero_recibo', 'plataforma', name='uq_recibo_plataforma'),
    )