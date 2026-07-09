#!/usr/bin/env python3
"""
create_admin.py - Script para crear un usuario administrador en OfficePing desde terminal/código.

Uso:
    python3 create_admin.py --email admin@empresa.com --nombre "Administrador" --password "Admin123!"
"""

import argparse
import sys
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models import User
from app.security import get_password_hash


def create_admin_user(email: str, nombre: str, password: str) -> None:
    # Asegurar creación de tablas
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"[ERROR] Ya existe un usuario con el correo: {email}")
            sys.exit(1)

        admin = User(
            email=email,
            nombre=nombre,
            password_hash=get_password_hash(password),
            rol="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"[SUCCESS] Usuario administrador creado con éxito: {admin.email} (ID: {admin.id})")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crear usuario administrador de OfficePing")
    parser.add_argument("--email", required=True, help="Correo electrónico del administrador")
    parser.add_argument("--nombre", required=True, help="Nombre del administrador")
    parser.add_argument("--password", required=True, help="Contraseña del administrador")

    args = parser.parse_args()
    create_admin_user(args.email, args.nombre, args.password)
