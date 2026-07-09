"""
models.py - Modelo SQLAlchemy para la tabla de usuarios/empleados de OfficePing.
"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """
    Representa a un empleado registrado en el sistema OfficePing.
    Campos:
      - id: Clave primaria autoincremental.
      - email: Correo corporativo único, usado como identificador principal.
      - nombre: Nombre visible del empleado en la interfaz.
      - rol: Rol dentro del sistema ('admin' o 'user').
      - created_at: Timestamp de creación del registro.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    rol: Mapped[str] = mapped_column(String, nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} rol={self.rol!r}>"
