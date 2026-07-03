"""
routers/users.py - CU-04: Listado de compañeros para envío de alertas.

Endpoint:
  GET /api/users
    - Retorna la lista completa de empleados registrados.
    - Usada por el panel principal del cliente para poblar la lista de contactos.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/api", tags=["Usuarios"])


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="Listar todos los empleados registrados",
    description=(
        "Retorna la lista completa de empleados en el sistema. "
        "El cliente la usa para renderizar la pantalla de selección de destinatario "
        "al momento de enviar una alerta."
    ),
)
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Obtiene todos los empleados ordenados por nombre ascendente."""
    users = db.query(User).order_by(User.nombre.asc()).all()
    return users  # type: ignore[return-value]
