"""
database.py - Configuración de SQLAlchemy con SQLite para OfficePing.
Crea el engine, la sesión y la base de clases declarativa.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Ruta de la base de datos SQLite dentro del directorio backend
DATABASE_URL = "sqlite:///./officeping.db"

# echo=False en producción para no loggear cada query SQL
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necesario para SQLite con FastAPI
    echo=False,
)

# Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Clase base declarativa para todos los modelos ORM
class Base(DeclarativeBase):
    pass
