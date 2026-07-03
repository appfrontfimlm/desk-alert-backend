"""
main.py - Entrypoint principal de la aplicación FastAPI de OfficePing.

Responsabilidades:
  - Instanciar la aplicación FastAPI con metadata descriptiva.
  - Configurar CORS para permitir peticiones desde los clientes Electron/React.
  - Crear las tablas en SQLite automáticamente al arrancar (si no existen).
  - Registrar todos los routers (auth, users, admin, websockets).
  - Exponer un endpoint de health-check en la raíz.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, users, admin, websockets

# ─────────────────────────────────────────────────────────
# Configuración de logging
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("officeping")

# ─────────────────────────────────────────────────────────
# Instancia de FastAPI
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="OfficePing API",
    description=(
        "Backend centralizado del sistema de alertas de oficina OfficePing. "
        "Gestiona empleados, autenticación y comunicación en tiempo real via WebSockets."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─────────────────────────────────────────────────────────
# Configuración de CORS
# Permite peticiones desde el cliente Electron/React en
# modo desarrollo y orígenes locales habituales.
# ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
# Creación automática de tablas en SQLite al arrancar
# ─────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    """
    Crea las tablas definidas en los modelos SQLAlchemy si no existen aún.
    Esto evita tener que ejecutar migraciones manualmente en desarrollo.
    """
    logger.info("Inicializando base de datos SQLite (officeping.db)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos lista.")


# ─────────────────────────────────────────────────────────
# Registro de Routers
# ─────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(websockets.router)


# ─────────────────────────────────────────────────────────
# Health-check endpoint
# ─────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health check del servidor")
async def root() -> dict:
    """Endpoint de verificación de vida del servidor. Útil para monitoreo."""
    return {"status": "ok", "app": "OfficePing API", "version": "1.0.0"}
