"""Criação do banco, sessão e operações CRUD."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from .models import Atendimento, Base


def ensure_database_directory(url: str) -> None:
    """Cria o diretório do arquivo de banco, quando o dialeto for SQLite.

    O SQLite não cria o diretório do arquivo: sem esta etapa, uma cópia limpa
    do repositório falha com ``unable to open database file`` (BUG-001).
    """
    parsed = make_url(url)
    if not parsed.drivername.startswith("sqlite"):
        return
    database = parsed.database
    if not database or database == ":memory:":
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(url: str) -> sessionmaker:
    """Prepara o banco e devolve a fábrica de sessões."""
    ensure_database_directory(url)
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker) -> Iterator[Session]:
    """Abre uma sessão transacional, com ``commit`` ao final e ``rollback`` em erro."""
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def find_by_protocol(session: Session, protocol: str) -> Atendimento | None:
    """Devolve o atendimento com o protocolo informado, se existir."""
    return session.scalar(select(Atendimento).where(Atendimento.protocolo == protocol))


def delete_by_protocol(session: Session, protocol: str) -> bool:
    """Remove o atendimento com o protocolo informado.

    Returns:
        ``True`` se havia um registro para remover.
    """
    item = find_by_protocol(session, protocol)
    if not item:
        return False
    session.delete(item)
    return True
