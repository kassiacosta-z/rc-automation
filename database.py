"""Inicialização do banco de dados (SQLite por padrão).

Define engine, SessionLocal e Base para uso com SQLAlchemy 2.x.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import config


class Base(DeclarativeBase):
    pass


# echo=False para não poluir logs; pode ser habilitado via env no futuro
engine = create_engine(config.DATABASE_URL, echo=False, future=True)

# expire_on_commit=False para permitir acesso aos atributos após commit
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Cria as tabelas conforme modelos registrados em Base.metadata."""
    # Importações locais para registrar mapeamentos antes do create_all
    import models  # noqa: F401  

    Base.metadata.create_all(bind=engine)


