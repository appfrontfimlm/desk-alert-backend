"""
routers/websockets.py - Motor de comunicación en tiempo real de OfficePing.

Endpoint:
  WebSocket /ws

Protocolo de mensajes JSON:

  1. register (Client -> Server)
     { "type": "register", "email": "juan@empresa.com" }
     -> Registra la conexión activa en el ConnectionManager.

  2. send_alert (Client -> Server)
     { "type": "send_alert", "from_email": "...", "to_email": "...", "message": "..." }
     -> El servidor busca al destinatario en active_connections y le reenvía
        un mensaje receive_alert con el nombre del emisor.

  3. receive_alert (Server -> Destinatario Client)
     { "type": "receive_alert", "from_name": "Juan", "from_email": "...", "message": "..." }
     -> Disparado en el cliente del receptor para abrir el pop-up intrusivo.

Manejo de desconexiones:
  Todo el loop de escucha está envuelto en try/except con WebSocketDisconnect
  y Exception general. En cualquier caso, se limpia el mapa active_connections.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.connection_manager import manager

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger("officeping.ws")


def _get_user_name(email: str) -> str | None:
    """
    Consulta sincrónicamente la BD para obtener el nombre del emisor.
    Se abre una sesión propia porque el endpoint de WS no usa el ciclo
    de vida de Depends(get_db) de la misma forma que los endpoints REST.
    """
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        return user.nombre if user else None
    finally:
        db.close()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Endpoint WebSocket principal de OfficePing.

    Flujo de vida de una conexión:
    1. El cliente se conecta. Se acepta la conexión sin email (se registra luego).
    2. El primer mensaje esperado es de tipo 'register' con el email del empleado.
    3. El servidor entra en un loop infinito esperando mensajes.
    4. Al recibir 'send_alert', se enruta el payload al destinatario.
    5. Al desconectarse (WebSocketDisconnect o cualquier error), se limpia el mapa.
    """
    # Aceptar la conexión antes de conocer el email; el email llega en el primer mensaje.
    await websocket.accept()

    registered_email: str | None = None  # Rastrea qué email corresponde a este socket

    try:
        while True:
            # ── Esperar mensaje del cliente ──────────────────────────────────
            raw = await websocket.receive_text()

            try:
                data: dict = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Mensaje WS no es JSON válido: %r", raw)
                await websocket.send_json({
                    "type": "error",
                    "detail": "El mensaje debe ser un JSON válido.",
                })
                continue

            msg_type: str = data.get("type", "")

            # ── Manejar tipo 'register' ──────────────────────────────────────
            if msg_type == "register":
                email: str | None = data.get("email")
                if not email:
                    await websocket.send_json({
                        "type": "error",
                        "detail": "El mensaje 'register' debe incluir el campo 'email'.",
                    })
                    continue

                # Registrar (o re-registrar si ya tenía una conexión previa)
                # Nota: connect() hace accept() internamente, pero aquí ya aceptamos arriba.
                # Por eso registramos directamente en el mapa sin llamar manager.connect().
                manager._connections[email] = websocket  # noqa: SLF001
                registered_email = email
                logger.info("WS registrado: %s (total activos: %d)", email, manager.count)

                await websocket.send_json({
                    "type": "registered",
                    "email": email,
                    "message": f"Bienvenido, {email}. Conexión registrada exitosamente.",
                })

            # ── Manejar tipo 'send_alert' ────────────────────────────────────
            elif msg_type == "send_alert":
                from_email: str | None = data.get("from_email")
                to_email: str | None = data.get("to_email")
                message: str = data.get("message", "")

                if not from_email or not to_email:
                    await websocket.send_json({
                        "type": "error",
                        "detail": "El mensaje 'send_alert' requiere 'from_email' y 'to_email'.",
                    })
                    continue

                # Obtener el nombre del emisor para enriquecer el payload
                from_name = _get_user_name(from_email) or from_email

                # Construir el payload que recibirá el destinatario
                alert_payload = {
                    "type": "receive_alert",
                    "from_name": from_name,
                    "from_email": from_email,
                    "message": message,
                }

                sent = await manager.send_to(to_email, alert_payload)

                # Confirmar al emisor el resultado del envío
                if sent:
                    await websocket.send_json({
                        "type": "alert_sent",
                        "to_email": to_email,
                        "message": "Alerta enviada exitosamente.",
                    })
                    logger.info("Alerta enviada: %s -> %s", from_email, to_email)
                else:
                    await websocket.send_json({
                        "type": "alert_failed",
                        "to_email": to_email,
                        "message": f"El empleado '{to_email}' no está conectado en este momento.",
                    })
                    logger.warning(
                        "Alerta no entregada: '%s' no está conectado. Emisor: %s",
                        to_email,
                        from_email,
                    )

            # ── Tipo de mensaje desconocido ──────────────────────────────────
            else:
                logger.warning("Tipo de mensaje WS desconocido: %r", msg_type)
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Tipo de mensaje desconocido: '{msg_type}'. "
                              "Tipos válidos: 'register', 'send_alert'.",
                })

    except WebSocketDisconnect:
        # Desconexión limpia: el cliente cerró la app, la pestaña o la laptop
        logger.info("Cliente desconectado limpiamente: %s", registered_email or "desconocido")

    except Exception as exc:  # noqa: BLE001
        # Error inesperado: socket roto, pérdida de red abrupta, etc.
        logger.error(
            "Error inesperado en WS de '%s': %s",
            registered_email or "desconocido",
            exc,
        )

    finally:
        # ── REGLA CRÍTICA: Siempre limpiar active_connections ────────────────
        # Sin esto, el servidor intentaría enviar alertas a sockets muertos
        # y /api/admin/connections mostraría estados incorrectos.
        if registered_email:
            manager.disconnect(registered_email)
