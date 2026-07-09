# Especificación y Contexto de Desarrollo: Backend (OfficePing)

Este documento contiene el contexto arquitectónico, los requerimientos técnicos, los modelos de datos y el protocolo de comunicación necesarios para desarrollar el **Backend** del sistema **OfficePing**.

---

## 1. Resumen y Rol del Backend
El backend es un servidor centralizado encargado de gestionar la autenticación e identificación de usuarios, la persistencia de datos (empleados y roles) y el enrutamiento en tiempo real de alertas intrusivas para oficinas a través de WebSockets bidireccionales.

### Stack Tecnológico
* **Lenguaje / Framework Principal:** Python 3.10+ con **FastAPI**.
* **Base de Datos y ORM:** **SQLite** utilizando **SQLAlchemy** para la persistencia local de usuarios.
* **Comunicación en Tiempo Real:** WebSockets nativos de FastAPI (`websockets`).
* **Servidor ASGI:** Uvicorn (o Hypercorn/Gunicorn con workers Uvicorn).

---

## 2. Modelos de Datos y Estructuras en Memoria

### A. Modelo de Base de Datos (SQLAlchemy - SQLite)
#### Tabla: `usuarios` / `empleados`
| Campo | Tipo de Dato | Descripción |
| :--- | :--- | :--- |
| `id` | Integer | Clave primaria autoincremental |
| `email` | String | Único, utilizado como identificador principal del empleado |
| `password_hash` | String | Hash seguro de la contraseña almacenado con `bcrypt` |
| `nombre` | String | Nombre visible del empleado (ej. "Juan Pérez") |
| `rol` | String | Rol dentro del sistema: `"admin"` o `"user"` |
| `created_at` | DateTime | Fecha y hora de registro del empleado |

### B. Seguridad y Sesiones (JWT Persistente)
* Todas las sesiones se administran mediante tokens **JWT sin expiración (`exp` omitido)** emitidos por el endpoint `/api/auth/login`.
* Las rutas protegidas del backend requieren la cabecera HTTP:
  ```http
  Authorization: Bearer <access_token>
  ```

### C. Estado de Conexión en Memoria (WebSockets)
Para permitir el enrutamiento inmediato de alertas entre empleados sin latencia, el backend mantendrá un mapa o diccionario activo en memoria dentro del ciclo de vida de FastAPI:
```python
active_connections: dict[str, WebSocket] = {}
# Mapea: email_del_usuario -> Instancia activa de WebSocket
```

---

## 3. Protocolo y Estructura de Comunicación por WebSockets
Los mensajes transmitidos a través del WebSocket deben ser estrictamente en formato **JSON**.

### A. Registro de Conexión (Client -> Server)
Enviado por el cliente inmediatamente después de abrir el canal de WebSocket adjuntando su token JWT de sesión para validación:
```json
{
  "type": "register",
  "email": "juan@empresa.com",
  "token": "eyJhbGciOiJIUzI1NiIsIn..."
}
```
* **Acción del Backend:** Al recibir este mensaje, se decodifica y verifica el token JWT. Si es válido y coincide con `email`, se registra la conexión en `active_connections["juan@empresa.com"] = websocket`.

### B. Envío de Alerta (Client -> Server)
Enviado por el empleado emisor cuando desea llamar la atención de un compañero.
```json
{
  "type": "send_alert",
  "from_email": "juan@empresa.com",
  "to_email": "pedro@empresa.com",
  "message": "Hola, necesito que te quites los audífonos un momento."
}
```
* **Acción del Backend:** Buscar a `"pedro@empresa.com"` en `active_connections`. Si está conectado, enviarle un payload de recepción de alerta.

### C. Recepción de Alerta (Server -> Destinatario Client)
Enviado por el backend únicamente al socket del empleado destinatario.
```json
{
  "type": "receive_alert",
  "from_name": "Juan",
  "from_email": "juan@empresa.com",
  "message": "Hola, necesito que te quites los audífonos un momento."
}
```

---

## 4. Endpoints REST y Especificación de Casos de Uso

### CU-01: Autenticación e Inicio de Sesión
* **Endpoint:** `POST /api/auth/login`
* **Payload Request:** `{ "email": "empleado@empresa.com", "password": "SecretPassword123!" }`
* **Comportamiento:**
  1. Consulta en la base de datos SQLite si el correo existe y valida el hash con `bcrypt`.
  2. **Si es válido:** Retorna HTTP 200 con el token JWT de acceso sin expiración y el perfil del usuario:
     ```json
     {
       "access_token": "eyJhbGciOi...",
       "token_type": "bearer",
       "user": { "id": 1, "email": "...", "nombre": "Juan", "rol": "user" }
     }
     ```
  3. **Si es incorrecto:** Retorna HTTP 401 Unauthorized.

### CU-02: Gestión de Usuarios - Crear Empleado (Panel Admin)
* **Endpoint:** `POST /api/admin/users`
* **Permisos:** Requiere validar que el usuario que realiza la petición sea administrador (`rol == "admin"`).
* **Payload Request:** `{ "nombre": "Pedro", "email": "pedro@empresa.com", "password": "Pass123!", "rol": "user" }`
* **Comportamiento:** Hashea la contraseña con `bcrypt`, crea el registro en SQLite y retorna el usuario creado con HTTP 201.

### CU-02.1: Gestión de Usuarios - Editar Empleado (Panel Admin)
* **Endpoint:** `PUT /api/admin/users/{user_id}`
* **Permisos:** Requiere validar que el usuario sea administrador.
* **Payload Request:** `{ "nombre": "Pedro López", "rol": "admin" }`
* **Comportamiento:** Actualiza el nombre y el rol del usuario en SQLite. El correo electrónico permanece inmutable. Retorna HTTP 200 con el usuario actualizado.

### CU-02.2: Gestión de Usuarios - Eliminar Empleado (Panel Admin)
* **Endpoint:** `DELETE /api/admin/users/{user_id}`
* **Permisos:** Requiere validar que el usuario sea administrador.
* **Comportamiento:** Impide eliminar la cuenta del administrador autenticado. Si el empleado está conectado al WebSocket, lo desconecta en memoria e inmediatamente elimina su registro de SQLite devolviendo HTTP 204.

### CU-03: Monitoreo de Conexiones Activas (Panel Admin)
* **Endpoint:** `GET /api/admin/connections`
* **Comportamiento:** Retorna la lista de empleados y su estado en tiempo real (`online` / `offline`).

### CU-04: Listado de Compañeros para Envío de Alertas
* **Endpoint:** `GET /api/users`
* **Seguridad:** Requiere token JWT en cabecera `Authorization: Bearer <token>`.
* **Comportamiento:** Retorna la lista ordenada de usuarios registrados y su estado de conexión.

---

## 5. Instrucciones Técnicas y Creación de Administrador Inicial

### A. Creación del Primer Administrador (`create_admin.py`)
Para crear el administrador inicial con contraseña en entornos de desarrollo o producción, se ejecuta el script CLI incluido:
```bash
python3 create_admin.py --email admin@empresa.com --nombre "Administrador" --password "Admin123!"
```

### B. Robustez en WebSockets y Manejo de Desconexiones
Es **obligatorio** envolver la escucha del WebSocket (`await websocket.receive_text()`) en bloques `try-except` (manejando `WebSocketDisconnect` y excepciones generales).
* **Regla Crítica:** Si un cliente pierde la conexión, el backend debe remover inmediatamente su correo del diccionario `active_connections`.
