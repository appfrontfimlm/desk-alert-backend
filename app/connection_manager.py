"""
connection_manager.py - Gestor centralizado de conexiones WebSocket activas.

Mantiene en memoria el mapa de email -> WebSocket para enrutar alertas
entre empleados en tiempo real sin latencia de base de datos.
"""

import logging
from fastapi import WebSocket

logger = logging.getLogger("officeping.ws")


class ConnectionManager:
    """
    Gestiona el ciclo de vida de todas las conexiones WebSocket activas.

    Proporciona métodos para:
      - Conectar / desconectar sockets manteniendo el diccionario limpio.
      - Enviar mensajes a un destinatario específico por email.
      - Broadcast a todos los clientes conectados (usado por el admin).
    """

    def __init__(self) -> None:
        # email -> instancia activa de WebSocket
        self._connections: dict[str, WebSocket] = {}

    # ─── Ciclo de vida ────────────────────────────────────────────────────────

    async def connect(self, email: str, websocket: WebSocket) -> None:
        """Acepta la conexión y la registra en el mapa activo."""
        await websocket.accept()
        # Si el mismo email reconecta (ej. reload de la app), reemplazar la entrada
        self._connections[email] = websocket
        logger.info("WS conectado: %s  (total activos: %d)", email, self.count)

    def disconnect(self, email: str) -> None:
        """Elimina la conexión del mapa. Seguro si el email no existe."""
        removed = self._connections.pop(email, None)
        if removed is not None:
            logger.info(
                "WS desconectado: %s  (total activos: %d)", email, self.count
            )
        else:
            logger.warning(
                "Intento de desconexión de email no registrado: %s", email
            )

    # ─── Envío de mensajes ────────────────────────────────────────────────────

    async def send_to(self, email: str, payload: dict) -> bool:
        """
        Envía un mensaje JSON al WebSocket de un email específico.
        Retorna True si el envío fue exitoso, False si el destinatario
        no está conectado o si ocurre un error al enviar.
        """
        websocket = self._connections.get(email)
        if websocket is None:
            logger.warning("send_to: '%s' no está conectado.", email)
            return False

        try:
            await websocket.send_json(payload)
            return True
        except Exception as exc:
            logger.error(
                "Error al enviar mensaje a '%s': %s. Removiendo del mapa.", email, exc
            )
            # Si el socket está roto, limpiar la entrada
            self.disconnect(email)
            return False

    async def broadcast(self, payload: dict, exclude: str | None = None) -> None:
        """
        Envía un mensaje JSON a todos los clientes conectados.
        Opcionalmente excluye a un email específico (ej. el emisor).
        """
        disconnected: list[str] = []
        for email, websocket in self._connections.items():
            if email == exclude:
                continue
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                logger.error("Broadcast error para '%s': %s", email, exc)
                disconnected.append(email)

        # Limpiar sockets muertos encontrados durante el broadcast
        for email in disconnected:
            self.disconnect(email)

    # ─── Consultas de estado ──────────────────────────────────────────────────

    def is_connected(self, email: str) -> bool:
        """Indica si un email tiene una conexión WebSocket activa."""
        return email in self._connections

    def active_emails(self) -> list[str]:
        """Retorna la lista de emails con conexiones activas en este momento."""
        return list(self._connections.keys())

    @property
    def count(self) -> int:
        """Número total de conexiones activas."""
        return len(self._connections)


# Instancia singleton compartida por todos los routers
manager = ConnectionManager()
