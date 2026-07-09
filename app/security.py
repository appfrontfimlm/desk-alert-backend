"""
security.py - Utilidades criptográficas para autenticación y autorización en OfficePing.

Contiene:
  - Hash y verificación de contraseñas usando passlib (bcrypt).
  - Creación y verificación de tokens de acceso JWT (sin expiración por requerimiento del usuario).
"""

import os
from typing import Any
import jwt
from passlib.context import CryptContext

# Configuración de passlib para bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Clave secreta y algoritmo para JWT
SECRET_KEY = os.getenv("OFFICEPING_SECRET_KEY", "officeping_super_secret_jwt_key_2026")
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera un hash bcrypt a partir de una contraseña en texto plano."""
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any]) -> str:
    """
    Crea un token JWT de acceso.
    Por requerimiento del usuario, no incluye fecha de expiración ('exp'),
    permitiendo que la sesión permanezca activa hasta el cierre de sesión explícito.
    """
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decodifica y valida la firma de un token JWT.
    Retorna el payload si es válido, o None en caso de error.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
