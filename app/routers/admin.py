"""
routers/admin.py - Panel de administración de OfficePing.

Endpoints:
  POST /api/admin/users
    - CU-02: Crear un nuevo empleado en el sistema.
    - Requiere que quien hace la petición sea administrador (header X-Admin-Email).

  GET /api/admin/connections
    - CU-03: Monitoreo en tiempo real del estado de conexión de todos los empleados.
    - Cruza la tabla de usuarios con el mapa en memoria active_connections.

Nota sobre autenticación:
  En esta fase se usa un mecanismo simple de validación por header (X-Admin-Email).
  El header debe contener el email del administrador que realiza la acción.
  El backend verifica en la BD que ese email tenga rol='admin'.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.schemas import (
    ConnectionStatusResponse,
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
)
from app.connection_manager import manager
from app.security import get_password_hash

router = APIRouter(prefix="/api/admin", tags=["Administración"])


# ─── Dependencia interna: verificar que el solicitante es admin ───────────────

def _require_admin(
    x_admin_email: str = Header(
        ...,
        alias="X-Admin-Email",
        description="Email corporativo del administrador que realiza la acción.",
    ),
    db: Session = Depends(get_db),
) -> User:
    """
    Valida que el header X-Admin-Email corresponda a un usuario con rol 'admin'.
    Lanza HTTP 403 si no es administrador o HTTP 404 si el email no existe.
    """
    admin = db.query(User).filter(User.email == x_admin_email).first()

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario '{x_admin_email}' no existe en el sistema.",
        )

    if admin.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requiere rol de administrador para esta operación.",
        )

    return admin


# ─── CU-02: Crear empleado ────────────────────────────────────────────────────

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo empleado (requiere rol admin)",
    description=(
        "Crea un nuevo empleado en la base de datos SQLite. "
        "El solicitante debe enviar su email en el header 'X-Admin-Email' "
        "y dicho email debe corresponder a un usuario con rol 'admin'."
    ),
)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(_require_admin),
) -> UserResponse:
    """
    Flujo:
    1. Verificar que el email del nuevo empleado no esté ya registrado.
    2. Crear el registro en SQLite.
    3. Retornar el perfil creado con HTTP 201.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un empleado registrado con el correo '{payload.email}'.",
        )

    new_user = User(
        nombre=payload.nombre,
        email=str(payload.email),
        password_hash=get_password_hash(payload.password),
        rol=payload.rol,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user  # type: ignore[return-value]


# ─── CU-02.1: Editar empleado ─────────────────────────────────────────────────

@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Actualizar nombre y rol de un empleado (requiere rol admin)",
    description=(
        "Actualiza el nombre y el rol de un empleado existente. "
        "El correo electrónico permanece inmutable."
    ),
)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(_require_admin),
) -> UserResponse:
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El empleado con ID {user_id} no existe.",
        )

    target_user.nombre = payload.nombre
    target_user.rol = payload.rol
    db.commit()
    db.refresh(target_user)

    return target_user  # type: ignore[return-value]


# ─── CU-02.2: Eliminar empleado ───────────────────────────────────────────────

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un empleado (requiere rol admin)",
    description=(
        "Elimina a un empleado de la base de datos. No permite que el administrador "
        "elimine su propia cuenta. Desconecta su WebSocket si está activo."
    ),
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(_require_admin),
) -> None:
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El empleado con ID {user_id} no existe.",
        )

    if target_user.email == _admin.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta de administrador.",
        )

    # Desconectar el WebSocket si el empleado está conectado
    manager.disconnect(target_user.email)

    db.delete(target_user)
    db.commit()


# ─── CU-03: Monitoreo de conexiones activas ───────────────────────────────────

@router.get(
    "/connections",
    response_model=list[ConnectionStatusResponse],
    summary="Estado de conexión de todos los empleados",
    description=(
        "Retorna la lista completa de empleados con su estado de conexión WebSocket "
        "actual ('online' / 'offline'). Cruza la tabla de usuarios en SQLite con el "
        "mapa de conexiones activas en memoria."
    ),
)
def get_connections(
    db: Session = Depends(get_db),
    _admin: User = Depends(_require_admin),
) -> list[ConnectionStatusResponse]:
    """
    Flujo:
    1. Obtener todos los usuarios de la BD.
    2. Para cada uno, verificar si su email está en active_connections (in-memory).
    3. Retornar lista con status 'online' / 'offline'.
    """
    all_users = db.query(User).order_by(User.nombre.asc()).all()

    return [
        ConnectionStatusResponse(
            email=user.email,
            nombre=user.nombre,
            status="online" if manager.is_connected(user.email) else "offline",
        )
        for user in all_users
    ]
