"""
schemas.py - Schemas de Pydantic para validación y serialización de datos en OfficePing.
Separados en schemas de Request (entrada) y Response (salida).
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr


# ─────────────────────────────────────────────────────────
# Schemas de Respuesta (Response)
# ─────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Datos de usuario devueltos al cliente (sin información sensible)."""
    id: int
    email: EmailStr
    nombre: str
    rol: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectionStatusResponse(BaseModel):
    """Representa el estado de conexión de un empleado para el panel de admin."""
    email: str
    nombre: str
    status: Literal["online", "offline"]


# ─────────────────────────────────────────────────────────
# Schemas de Petición (Request)
# ─────────────────────────────────────────────────────────

class IdentifyRequest(BaseModel):
    """Payload para el endpoint de identificación inicial del empleado."""
    email: EmailStr


class CreateUserRequest(BaseModel):
    """Payload para crear un nuevo empleado (usado por el administrador)."""
    nombre: str
    email: EmailStr
    rol: Literal["admin", "user"] = "user"


# ─────────────────────────────────────────────────────────
# Schemas de Mensajes WebSocket (JSON Protocol)
# ─────────────────────────────────────────────────────────

class WSRegisterMessage(BaseModel):
    """Mensaje de registro enviado por el cliente al conectarse al WS."""
    type: Literal["register"]
    email: EmailStr


class WSSendAlertMessage(BaseModel):
    """Mensaje de envío de alerta entre empleados a través del WS."""
    type: Literal["send_alert"]
    from_email: EmailStr
    to_email: EmailStr
    message: str


class WSReceiveAlertMessage(BaseModel):
    """Payload de alerta enviado por el servidor al empleado destinatario."""
    type: Literal["receive_alert"]
    from_name: str
    from_email: str
    message: str
