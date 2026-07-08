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
| `nombre` | String | Nombre visible del empleado (ej. "Juan Pérez") |
| `rol` | String | Rol dentro del sistema: `"admin"` o `"user"` |
| `created_at` | DateTime | Fecha y hora de registro del empleado |

### B. Estado de Conexión en Memoria (WebSockets)
Para permitir el enrutamiento inmediato de alertas entre empleados sin latencia, el backend mantendrá un mapa o diccionario activo en memoria dentro del ciclo de vida de FastAPI:
```python
# Ejemplo conceptual de diccionario en memoria
active_connections: dict[str, WebSocket] = {}
# Mapea: email_del_usuario -> Instancia activa de WebSocket
```

---

## 3. Protocolo y Estructura de Comunicación por WebSockets
Los mensajes transmitidos a través del WebSocket deben ser estrictamente en formato **JSON**.

### A. Registro de Conexión (Client -> Server)
Enviado por el cliente de escritorio inmediatamente después de abrir el canal de WebSocket tras haber sido autenticado/identificado.
```json
{
  "type": "register",
  "email": "juan@empresa.com"
}
```
* **Acción del Backend:** Al recibir este mensaje, registrar o actualizar la conexión en `active_connections["juan@empresa.com"] = websocket`.

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

### CU-01: Identificación de Empleado (Login/Registro Inicial)
* **Endpoint:** `POST /api/auth/identify`
* **Payload Request:** `{ "email": "empleado@empresa.com" }`
* **Comportamiento:**
  1. Consulta en la base de datos SQLite si el correo existe.
  2. **Si existe:** Retorna HTTP 200 con los datos del usuario: `{ "id": 1, "email": "...", "nombre": "Juan", "rol": "user" }`.
  3. **Si no existe:** Retorna HTTP 404 (o 403) con el mensaje de error: *"El usuario no existe. Debe ser registrado por un administrador"*.

### CU-02: Gestión de Usuarios - Crear Empleado (Panel Admin)
* **Endpoint:** `POST /api/admin/users`
* **Permisos:** Requiere validar que el usuario que realiza la petición sea administrador (`rol == "admin"`).
* **Payload Request:** `{ "nombre": "Pedro", "email": "pedro@empresa.com", "rol": "user" }`
* **Comportamiento:** Crea el registro en SQLite y retorna el usuario creado con HTTP 201.

### CU-02.1: Gestión de Usuarios - Editar Empleado (Panel Admin)
* **Endpoint:** `PUT /api/admin/users/{user_id}`
* **Permisos:** Requiere validar que el usuario que realiza la petición sea administrador (`header X-Admin-Email`).
* **Payload Request:** `{ "nombre": "Pedro López", "rol": "admin" }`
* **Comportamiento:** Actualiza el nombre y el rol del usuario en SQLite. El correo electrónico permanece inmutable. Retorna HTTP 200 con el usuario actualizado.

### CU-02.2: Gestión de Usuarios - Eliminar Empleado (Panel Admin)
* **Endpoint:** `DELETE /api/admin/users/{user_id}`
* **Permisos:** Requiere validar que el usuario que realiza la petición sea administrador (`header X-Admin-Email`).
* **Comportamiento:** Impide eliminar la cuenta del administrador autenticado. Si el empleado está conectado al WebSocket, lo desconecta en memoria e inmediatamente elimina su registro de SQLite devolviendo HTTP 204.

### CU-03: Monitoreo de Conexiones Activas (Panel Admin)
* **Endpoint:** `GET /api/admin/connections`
* **Comportamiento:**
  1. Consulta todos los usuarios en la base de datos SQLite.
  2. Cruza la lista de usuarios con las claves del diccionario `active_connections`.
  3. Retorna una lista de objetos con el estado actual:
     ```json
     [
       { "email": "juan@empresa.com", "nombre": "Juan", "status": "online" },
       { "email": "pedro@empresa.com", "nombre": "Pedro", "status": "offline" }
     ]
     ```

### CU-04: Listado de Compañeros para Envío de Alertas
* **Endpoint:** `GET /api/users`
* **Comportamiento:** Retorna la lista de usuarios registrados para que el cliente pueda renderizar la interfaz de selección y envío de alertas.

---

## 5. Instrucciones Técnicas y Requerimientos Críticos

### A. Robustez en WebSockets y Manejo de Desconexiones
Es **obligatorio** envolver la escucha del WebSocket (`await websocket.receive_text()`) en bloques `try-except` (manejando `WebSocketDisconnect` y excepciones generales).
* **Regla Crítica:** Si un cliente pierde la conexión (ej. por cerrar la laptop, suspensión, pérdida de red o cierre involuntario), el backend **debe remover inmediatamente** su correo del diccionario `active_connections`.
* Esto previene fugas de memoria, caídas del servidor por intentos de envío a sockets muertos y asegura la exactitud del monitoreo de conexiones (`/api/admin/connections`).

### B. Configuración CORS
* Configurar `CORSMiddleware` en FastAPI para permitir peticiones entrantes desde los clientes de escritorio Electron/React tanto en modo desarrollo (ej. `http://localhost:5173`, `http://localhost:3000`) como desde esquemas locales en producción si procede.

---

## 6. Plan de Desarrollo Sugerido para el Backend
1. **Fase 1: Estructura y Base de Datos:**
   - Configuración de FastAPI y SQLAlchemy con SQLite.
   - Definición del modelo `User` y creación automática de tablas.
2. **Fase 2: APIs REST de Identificación y Administración:**
   - Implementación de los endpoints `/api/auth/identify`, `/api/users` y `/api/admin/users`.
3. **Fase 3: Motor de WebSockets y Conexiones:**
   - Implementación del endpoint WebSocket `/ws` o `/ws/{email}`.
   - Creación y mantenimiento en tiempo real del diccionario `active_connections`.
   - Implementación y prueba de la lógica de reenrutamiento de mensajes `send_alert` -> `receive_alert`.
4. **Fase 4: Monitoreo y Validación de Desconexiones:**
   - Implementación de `/api/admin/connections`.
   - Pruebas de resiliencia desconectando abruptamente sockets para verificar la limpieza de `active_connections`.
