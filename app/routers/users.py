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
from app.routers.websockets import manager

router = APIRouter(prefix="/api", tags=["Usuarios"])


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="Listar todos los empleados registrados",
    description=(
        "Retorna la lista completa de empleados en el sistema junto con su estado de conexión "
        "en tiempo real ('online'/'offline'). El cliente la usa para renderizar la pantalla "
        "de selección de destinatario al momento de enviar una alerta."
    ),
)
def list_users(db: Session = Depends(get_db)) -> list[UserResponse]:
    """Obtiene todos los empleados ordenados por nombre ascendente y su estado de socket."""
    users = db.query(User).order_by(User.nombre.asc()).all()
    result: list[UserResponse] = []
    for u in users:
        is_online = manager.is_connected(u.email)
        result.append(
            UserResponse(
                id=u.id,
                email=u.email,
                nombre=u.nombre,
                rol=u.rol,
                created_at=u.created_at,
                status="online" if is_online else "offline",
            )
        )
    return result
