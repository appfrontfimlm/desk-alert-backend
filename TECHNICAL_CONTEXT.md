# TECHNICAL_CONTEXT.md — OfficePing Backend API

Referencia técnica completa del backend implementado en **FastAPI**.
Este documento está dirigido al equipo de frontend (Electron + React) para que
pueda integrar la aplicación de escritorio con el servidor sin ambigüedades.

---

## Información General del Servidor

| Parámetro | Valor |
|-----------|-------|
| **URL Base (desarrollo)** | `http://localhost:8000` |
| **WebSocket Base** | `ws://localhost:8000` |
| **Documentación interactiva (Swagger)** | `http://localhost:8000/docs` |
| **Documentación alternativa (ReDoc)** | `http://localhost:8000/redoc` |
| **Framework** | FastAPI 0.111.0 + Python 3.10+ |
| **Base de datos** | SQLite (`officeping.db`) |
| **Formato de mensajes** | JSON (`Content-Type: application/json`) |

### Iniciar el servidor

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## CORS Configurado

El servidor ya tiene CORS habilitado para los siguientes orígenes. El frontend
puede hacer peticiones HTTP desde cualquiera de estos hosts sin problemas:

```
http://localhost:3000
http://localhost:5173
http://localhost:5174
http://localhost:8080
```

> **Nota para Electron en producción:** Si la app carga desde el protocolo
> `file://` (renderer sin servidor local), se recomienda añadir ese origen
> al backend o usar `allowAllOrigins` temporalmente en desarrollo.

---

## Autenticación

El sistema usa un mecanismo simple por **header HTTP**. No hay tokens JWT ni
sesiones en esta versión.

| Tipo de endpoint | Requiere autenticación |
|------------------|------------------------|
| `POST /api/auth/identify` | ❌ No |
| `GET /api/users` | ❌ No |
| `POST /api/admin/users` | ✅ Header `X-Admin-Email` |
| `GET /api/admin/connections` | ✅ Header `X-Admin-Email` |
| `WebSocket /ws` | ❌ No (la identidad va en el primer mensaje JSON) |

### Header de administrador

Los endpoints de administración requieren este header en **cada petición**:

```
X-Admin-Email: admin@empresa.com
```

El backend verifica en la base de datos que ese email exista **y** tenga
`rol = "admin"`. Si no cumple, responde con error.

---

## Modelo de Datos — Usuario / Empleado

Estructura JSON que el backend devuelve cuando retorna información de un usuario:

```json
{
  "id": 1,
  "email": "juan@empresa.com",
  "nombre": "Juan Pérez",
  "rol": "user",
  "created_at": "2026-07-03T18:25:40.769901"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `integer` | Identificador único autoincremental |
| `email` | `string` (email válido) | Correo corporativo, identificador principal |
| `nombre` | `string` | Nombre visible del empleado |
| `rol` | `"admin"` \| `"user"` | Rol dentro del sistema |
| `created_at` | `string` (ISO 8601 UTC) | Fecha y hora de registro |

---

## REST API — Endpoints

---

### `GET /`
**Health check — verificar que el servidor está vivo**

No requiere parámetros ni autenticación.

#### Request
```
GET http://localhost:8000/
```

#### Response `200 OK`
```json
{
  "status": "ok",
  "app": "OfficePing API",
  "version": "1.0.0"
}
```

---

### `POST /api/auth/identify`
**Identificar/autenticar un empleado por su correo corporativo.**

Llamar este endpoint al iniciar la app con el email guardado localmente.
Si el backend responde 200, el usuario está registrado y puede usar la app.

#### Request

```
POST http://localhost:8000/api/auth/identify
Content-Type: application/json
```

**Body:**
```json
{
  "email": "juan@empresa.com"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `email` | `string` (email válido) | ✅ Sí | Correo corporativo del empleado |

#### Responses

**`200 OK` — Usuario encontrado:**
```json
{
  "id": 2,
  "email": "juan@empresa.com",
  "nombre": "Juan Pérez",
  "rol": "user",
  "created_at": "2026-07-03T18:25:40.769901"
}
```

**`404 Not Found` — El email no está registrado:**
```json
{
  "detail": "El usuario no existe en el sistema. Debe ser registrado por un administrador antes de poder identificarse."
}
```

**`422 Unprocessable Entity` — Email con formato inválido:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "value is not a valid email address"
    }
  ]
}
```

#### Ejemplo JavaScript (Fetch)
```javascript
async function identifyUser(email) {
  const response = await fetch('http://localhost:8000/api/auth/identify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });

  if (response.ok) {
    const user = await response.json();
    // Guardar en localStorage o config.json:
    // { id, email, nombre, rol }
    return user;
  }

  if (response.status === 404) {
    throw new Error('Usuario no registrado. Contacta al administrador.');
  }

  throw new Error('Error de identificación.');
}
```

---

### `GET /api/users`
**Listar todos los empleados registrados.**

Usada por el panel principal para poblar la lista de compañeros a los que
se les puede enviar una alerta. No requiere autenticación.

#### Request

```
GET http://localhost:8000/api/users
```

No tiene parámetros de query ni body.

#### Response `200 OK`

Array de objetos usuario, ordenado por nombre ascendente:

```json
[
  {
    "id": 1,
    "email": "admin@empresa.com",
    "nombre": "Administrador",
    "rol": "admin",
    "created_at": "2026-07-03T18:25:40.704190"
  },
  {
    "id": 2,
    "email": "juan@empresa.com",
    "nombre": "Juan Pérez",
    "rol": "user",
    "created_at": "2026-07-03T18:25:40.769901"
  },
  {
    "id": 3,
    "email": "pedro@empresa.com",
    "nombre": "Pedro López",
    "rol": "user",
    "created_at": "2026-07-03T18:25:40.791367"
  }
]
```

Si no hay usuarios registrados, devuelve un array vacío `[]`.

#### Ejemplo JavaScript (Fetch)
```javascript
async function getUsers() {
  const response = await fetch('http://localhost:8000/api/users');
  const users = await response.json();
  return users; // Array de usuarios
}
```

---

### `POST /api/admin/users`
**Registrar un nuevo empleado. Requiere rol admin.**

#### Request

```
POST http://localhost:8000/api/admin/users
Content-Type: application/json
X-Admin-Email: admin@empresa.com
```

**Body:**
```json
{
  "nombre": "Pedro López",
  "email": "pedro@empresa.com",
  "rol": "user"
}
```

| Campo | Tipo | Requerido | Valor por defecto | Descripción |
|-------|------|-----------|-------------------|-------------|
| `nombre` | `string` | ✅ Sí | — | Nombre visible del empleado |
| `email` | `string` (email válido) | ✅ Sí | — | Correo corporativo único |
| `rol` | `"admin"` \| `"user"` | ❌ No | `"user"` | Rol en el sistema |

**Header obligatorio:**

| Header | Tipo | Descripción |
|--------|------|-------------|
| `X-Admin-Email` | `string` (email) | Email del administrador que crea el usuario |

#### Responses

**`201 Created` — Empleado registrado exitosamente:**
```json
{
  "id": 3,
  "email": "pedro@empresa.com",
  "nombre": "Pedro López",
  "rol": "user",
  "created_at": "2026-07-03T18:25:40.791367"
}
```

**`409 Conflict` — El email ya está registrado:**
```json
{
  "detail": "Ya existe un empleado registrado con el correo 'pedro@empresa.com'."
}
```

**`403 Forbidden` — El email del header no es admin:**
```json
{
  "detail": "Acceso denegado: se requiere rol de administrador para esta operación."
}
```

**`404 Not Found` — El email del header no existe:**
```json
{
  "detail": "El usuario 'noexiste@empresa.com' no existe en el sistema."
}
```

**`422 Unprocessable Entity` — Falta el header `X-Admin-Email`:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "X-Admin-Email"],
      "msg": "Field required"
    }
  ]
}
```

#### Ejemplo JavaScript (Fetch)
```javascript
async function createEmployee(adminEmail, { nombre, email, rol = 'user' }) {
  const response = await fetch('http://localhost:8000/api/admin/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Email': adminEmail,
    },
    body: JSON.stringify({ nombre, email, rol }),
  });

  if (response.status === 201) {
    return await response.json(); // Nuevo usuario creado
  }

  const error = await response.json();
  throw new Error(error.detail);
}
```

---

### `GET /api/admin/connections`
**Monitoreo del estado de conexión WebSocket de todos los empleados.**

Retorna en tiempo real quién está conectado (`online`) y quién no (`offline`).
El estado se determina cruzando la base de datos con el mapa de sockets activos
en memoria del servidor.

#### Request

```
GET http://localhost:8000/api/admin/connections
X-Admin-Email: admin@empresa.com
```

No tiene parámetros de query ni body.

#### Response `200 OK`

Array ordenado por nombre, con el estado actual de cada empleado:

```json
[
  {
    "email": "admin@empresa.com",
    "nombre": "Administrador",
    "status": "offline"
  },
  {
    "email": "juan@empresa.com",
    "nombre": "Juan Pérez",
    "status": "online"
  },
  {
    "email": "pedro@empresa.com",
    "nombre": "Pedro López",
    "status": "offline"
  }
]
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `email` | `string` | Correo corporativo del empleado |
| `nombre` | `string` | Nombre visible |
| `status` | `"online"` \| `"offline"` | Estado de conexión WebSocket actual |

> **Importante:** Este endpoint refleja el estado **en el momento exacto de la petición**.
> Para monitoreo en tiempo real recomendamos pollear cada 5–10 segundos o
> implementar un canal WS de administración dedicado en el futuro.

#### Ejemplo JavaScript (Fetch)
```javascript
async function getConnections(adminEmail) {
  const response = await fetch('http://localhost:8000/api/admin/connections', {
    headers: { 'X-Admin-Email': adminEmail },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return await response.json(); // Array con status online/offline
}
```

---

## WebSocket — `/ws`

**URL de conexión:** `ws://localhost:8000/ws`

El WebSocket es el canal de comunicación principal en tiempo real de OfficePing.
Cada cliente de escritorio debe abrir **una sola conexión** y mantenerla activa
durante toda la sesión de la aplicación.

### Ciclo de vida de la conexión

```
Cliente                          Servidor
  │                                │
  ├─── Conectar ws://.../ ────────►│  Acepta la conexión
  │                                │
  ├─── { type: "register", ... } ─►│  Registra email en active_connections
  │◄── { type: "registered", ... } ┤  Confirmación de bienvenida
  │                                │
  │         (sesión activa)        │
  │                                │
  ├─── { type: "send_alert", ... }►│  Busca destinatario en active_connections
  │◄── { type: "alert_sent", ... } ┤  Confirmación al emisor
  │         (en socket del receptor):
  │         { type: "receive_alert", ... }  →  Pop-up en el receptor
  │                                │
  ├─── (cierra conexión / laptop)  │
  │                                │  Elimina email de active_connections
```

---

### Mensajes del Protocolo

> ⚠️ **Todos los mensajes son JSON. No se acepta otro formato.**
> Si el mensaje no es JSON válido, el servidor responde con `{ "type": "error" }`.

---

#### 1. `register` — Registrar conexión (Client → Server)

**Enviar inmediatamente después de conectar al WebSocket**, antes de cualquier otra acción.

```json
{
  "type": "register",
  "email": "juan@empresa.com"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `type` | `"register"` | ✅ Sí | Tipo de mensaje |
| `email` | `string` (email válido) | ✅ Sí | Email corporativo del empleado que se conecta |

**Respuesta del servidor (al emisor):**
```json
{
  "type": "registered",
  "email": "juan@empresa.com",
  "message": "Bienvenido, juan@empresa.com. Conexión registrada exitosamente."
}
```

---

#### 2. `send_alert` — Enviar alerta (Client → Server)

Enviado por el empleado emisor para llamar la atención de un compañero.

```json
{
  "type": "send_alert",
  "from_email": "juan@empresa.com",
  "to_email": "pedro@empresa.com",
  "message": "¡Necesito que te quites los audífonos!"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `type` | `"send_alert"` | ✅ Sí | Tipo de mensaje |
| `from_email` | `string` | ✅ Sí | Email del empleado que envía la alerta |
| `to_email` | `string` | ✅ Sí | Email del empleado destinatario |
| `message` | `string` | ✅ Sí | Mensaje opcional (puede ser string vacío `""`) |

**Respuesta al emisor — alerta entregada:**
```json
{
  "type": "alert_sent",
  "to_email": "pedro@empresa.com",
  "message": "Alerta enviada exitosamente."
}
```

**Respuesta al emisor — destinatario offline:**
```json
{
  "type": "alert_failed",
  "to_email": "pedro@empresa.com",
  "message": "El empleado 'pedro@empresa.com' no está conectado en este momento."
}
```

---

#### 3. `receive_alert` — Recibir alerta (Server → Receptor)

El servidor envía este mensaje **únicamente al socket del destinatario**.
Este es el evento que debe disparar el pop-up intrusivo en Electron.

```json
{
  "type": "receive_alert",
  "from_name": "Juan Pérez",
  "from_email": "juan@empresa.com",
  "message": "¡Necesito que te quites los audífonos!"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `type` | `"receive_alert"` | Identificador del evento |
| `from_name` | `string` | Nombre completo del emisor (obtenido de la BD) |
| `from_email` | `string` | Email del emisor |
| `message` | `string` | Mensaje personalizado del emisor |

> **⚡ Acción crítica del frontend:** Al recibir un mensaje con `type === "receive_alert"`,
> el proceso de React debe notificar al proceso principal de Electron vía IPC
> (`ipcRenderer.send(...)`) para que instancie la `BrowserWindow` intrusiva.

---

#### 4. `error` — Error de protocolo (Server → Client)

El servidor responde con este tipo si recibe un mensaje malformado o con un
`type` desconocido:

```json
{
  "type": "error",
  "detail": "El mensaje debe ser un JSON válido."
}
```

---

### Implementación del cliente WebSocket en JavaScript

```javascript
class OfficePingWebSocket {
  constructor(serverUrl = 'ws://localhost:8000/ws') {
    this.serverUrl = serverUrl;
    this.ws = null;
    this.userEmail = null;
    this.onAlertReceived = null; // callback: (payload) => void
  }

  connect(userEmail) {
    this.userEmail = userEmail;
    this.ws = new WebSocket(this.serverUrl);

    this.ws.onopen = () => {
      console.log('WebSocket conectado. Registrando usuario...');
      // 1. Registrar inmediatamente al conectar
      this.ws.send(JSON.stringify({
        type: 'register',
        email: userEmail,
      }));
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'registered':
          console.log('Conexión registrada:', data.message);
          break;

        case 'receive_alert':
          // ⚡ ACCIÓN CRÍTICA: disparar el pop-up intrusivo
          if (typeof this.onAlertReceived === 'function') {
            this.onAlertReceived(data);
          }
          break;

        case 'alert_sent':
          console.log('Alerta enviada a:', data.to_email);
          break;

        case 'alert_failed':
          console.warn('No se pudo entregar la alerta:', data.message);
          break;

        case 'error':
          console.error('Error del servidor WS:', data.detail);
          break;
      }
    };

    this.ws.onclose = () => {
      console.warn('WebSocket desconectado. Reconectando en 3s...');
      // Auto-reconexión
      setTimeout(() => this.connect(this.userEmail), 3000);
    };

    this.ws.onerror = (err) => {
      console.error('Error de WebSocket:', err);
    };
  }

  sendAlert(toEmail, message = '') {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket no está conectado.');
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'send_alert',
      from_email: this.userEmail,
      to_email: toEmail,
      message,
    }));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// ── Uso en React / Electron renderer ──────────────────────────
const wsClient = new OfficePingWebSocket();

// Al iniciar la app (después de identify):
wsClient.onAlertReceived = (payload) => {
  // En Electron renderer, notificar al proceso principal para el pop-up:
  window.api.triggerIntrusivePopup(payload);
  // payload = { type, from_name, from_email, message }
};

wsClient.connect('juan@empresa.com');

// Para enviar una alerta:
wsClient.sendAlert('pedro@empresa.com', '¡Necesito que te quites los audífonos!');
```

---

## Tabla Resumen de Todos los Endpoints

| Método | Ruta | Auth | Body / Params | Response exitoso |
|--------|------|------|---------------|------------------|
| `GET` | `/` | ❌ | — | `200` `{status, app, version}` |
| `POST` | `/api/auth/identify` | ❌ | Body: `{email}` | `200` `UserResponse` |
| `GET` | `/api/users` | ❌ | — | `200` `UserResponse[]` |
| `POST` | `/api/admin/users` | ✅ Header | Body: `{nombre, email, rol?}` | `201` `UserResponse` |
| `GET` | `/api/admin/connections` | ✅ Header | — | `200` `ConnectionStatusResponse[]` |
| `WS` | `/ws` | ❌ | JSON messages | Respuestas JSON tipadas |

---

## Códigos de Error HTTP — Referencia Rápida

| Código | Significado | Cuándo ocurre |
|--------|-------------|---------------|
| `200` | OK | Petición exitosa |
| `201` | Created | Recurso creado (nuevo empleado) |
| `404` | Not Found | Email no registrado en la BD |
| `403` | Forbidden | Email existe pero no tiene rol `admin` |
| `409` | Conflict | Email duplicado al crear empleado |
| `422` | Unprocessable Entity | Falta campo requerido o formato inválido |

---

## Flujo Completo de Integración (Checklist para el Frontend)

### Al iniciar la aplicación:
1. Leer el email guardado en `localStorage` / `config.json`.
2. Si hay email guardado → llamar `POST /api/auth/identify`.
   - Si `200`: guardar `{nombre, rol}` en estado global, ir a pantalla principal.
   - Si `404`: limpiar almacenamiento local, mostrar pantalla de login.
3. Conectar al WebSocket `ws://localhost:8000/ws`.
4. Enviar `{ type: "register", email }` inmediatamente al conectar.
5. Registrar el handler de `receive_alert` para disparar el pop-up intrusivo.

### En la pantalla principal:
6. Consumir `GET /api/users` para listar compañeros.
7. Al seleccionar destinatario y presionar "Llamar": enviar `send_alert` por WS.

### En el panel de administración (solo `rol === "admin"`):
8. Formulario de alta → `POST /api/admin/users` con header `X-Admin-Email`.
9. Tabla de estado → `GET /api/admin/connections` con header `X-Admin-Email`.
   - Se recomienda pollear cada **5–10 segundos** para mantener el estado actualizado.

### Al cerrar la aplicación / minimizar al tray:
10. Mantener la conexión WebSocket abierta (no cerrar al minimizar).
11. Al quitar la app del tray completamente → llamar `wsClient.disconnect()`.
