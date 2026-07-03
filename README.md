# OfficePing - Backend

Servidor centralizado de alertas en tiempo real para oficinas, construido con **FastAPI**, **SQLAlchemy/SQLite** y **WebSockets**.

---

## Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                # Entrypoint FastAPI: CORS, startup, routers
│   ├── database.py            # Engine SQLAlchemy + SessionLocal + Base
│   ├── models.py              # Modelo ORM User (tabla 'usuarios')
│   ├── schemas.py             # Schemas Pydantic (Request / Response / WS)
│   ├── dependencies.py        # Dependencia get_db para inyección de sesión
│   ├── connection_manager.py  # Singleton: mapa email->WebSocket en memoria
│   └── routers/
│       ├── __init__.py
│       ├── auth.py            # POST /api/auth/identify
│       ├── users.py           # GET  /api/users
│       ├── admin.py           # POST /api/admin/users | GET /api/admin/connections
│       └── websockets.py      # WebSocket /ws
├── requirements.txt
├── context.md
└── README.md
```

---

## Instalación

```bash
# 1. Crear y activar entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate      # Linux / macOS
# venv\Scripts\activate       # Windows

# 2. Instalar dependencias
pip install -r requirements.txt
```

---

## Ejecutar el Servidor

```bash
# Desde el directorio /backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

El servidor estará disponible en:
- **API REST + Docs:** http://localhost:8000/docs
- **WebSocket:** ws://localhost:8000/ws

---

## Endpoints REST

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/` | Health check | No |
| POST | `/api/auth/identify` | Identificar empleado por email | No |
| GET | `/api/users` | Listar todos los empleados | No |
| POST | `/api/admin/users` | Crear nuevo empleado | Header `X-Admin-Email` |
| GET | `/api/admin/connections` | Estado de conexión WS de todos | Header `X-Admin-Email` |

### Autenticación de Administrador

Los endpoints de `/api/admin/*` requieren el header:
```
X-Admin-Email: admin@empresa.com
```
El email debe corresponder a un usuario con `rol = "admin"` en la base de datos.

---

## Protocolo WebSocket (`ws://localhost:8000/ws`)

### 1. Registrar conexión (enviar inmediatamente al conectar)
```json
{ "type": "register", "email": "juan@empresa.com" }
```

### 2. Enviar alerta a un compañero
```json
{
  "type": "send_alert",
  "from_email": "juan@empresa.com",
  "to_email": "pedro@empresa.com",
  "message": "¡Necesito que te quites los audífonos!"
}
```

### 3. Recibir alerta (el servidor lo envía al destinatario)
```json
{
  "type": "receive_alert",
  "from_name": "Juan Pérez",
  "from_email": "juan@empresa.com",
  "message": "¡Necesito que te quites los audífonos!"
}
```

---

## Crear el primer administrador

La primera vez que se ejecuta el servidor, la BD está vacía. Para crear el primer administrador directamente desde SQLite:

```bash
# Con Python / SQLAlchemy (recomendado)
python3 -c "
from app.database import SessionLocal, Base, engine
from app.models import User
Base.metadata.create_all(bind=engine)
db = SessionLocal()
admin = User(nombre='Administrador', email='admin@empresa.com', rol='admin')
db.add(admin)
db.commit()
db.close()
print('Admin creado exitosamente.')
"
```

---

## Variables de Entorno y Configuración

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./officeping.db` | URL de la base de datos |
| `CORS_ORIGINS` | localhost varios | Orígenes permitidos |

---

## 🖥️ Despliegue en Producción (Servidor Local / VPS)

Para poner en producción el backend en la red de tu oficina de forma estable y permanente:

### Opción A: Gunicorn + Uvicorn Workers
```bash
pip install gunicorn
gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Opción B: Servicio Systemd (`/etc/systemd/system/officeping-backend.service`)
```ini
[Unit]
Description=OfficePing Backend API & WebSocket Server
After=network.target

[Service]
User=root
WorkingDirectory=/home/code/developer/Andres/desk-alert-project/backend
ExecStart=/home/code/developer/Andres/desk-alert-project/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Comandos para iniciar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now officeping-backend
sudo systemctl status officeping-backend
```

> 📚 **Nota:** Para instrucciones completas del empaquetado del cliente de escritorio (`AppImage` y `.deb`), consulta el **[README principal](../README.md)** en la raíz del proyecto.
