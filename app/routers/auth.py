"""
routers/auth.py - CU-01: Identificación / Login inicial del empleado.

Endpoint:
  POST /api/auth/identify
    - Verifica si el correo existe en la base de datos.
    - Si existe: retorna los datos del usuario (HTTP 200).
    - Si no existe: retorna HTTP 404 con mensaje de error explicativo.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.schemas import IdentifyRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post(
    "/identify",
    response_model=UserResponse,
    summary="Identificar empleado por correo corporativo",
    description=(
        "Recibe el correo corporativo del empleado y valida si está registrado "
        "en el sistema. Si está registrado, devuelve sus datos de perfil. "
        "Si no, retorna 404 indicando que debe ser dado de alta por un administrador."
    ),
)
def identify_user(payload: IdentifyRequest, db: Session = Depends(get_db)) -> UserResponse:
    """
    Flujo:
    1. Buscar al usuario en SQLite por su email.
    2. Si existe -> retornar perfil completo (id, email, nombre, rol, created_at).
    3. Si no existe -> HTTP 404 con mensaje descriptivo para el cliente de escritorio.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "El usuario no existe en el sistema. "
                "Debe ser registrado por un administrador antes de poder identificarse."
            ),
        )

    return user  # type: ignore[return-value]  # Pydantic lo serializará vía from_attributes
