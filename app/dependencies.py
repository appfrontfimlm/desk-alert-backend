"""
dependencies.py - Inyección de dependencias reutilizables en FastAPI.
Provee la sesión de base de datos como dependencia a los routers.
"""

from typing import Generator
from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Generador de sesión de base de datos.
    Se asegura de cerrar la sesión correctamente tras cada request,
    incluso si ocurre una excepción.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
