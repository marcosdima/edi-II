"""In-memory WebSocket room broker for real-time chat message broadcasting."""

import json
import threading
from typing import Any


class RoomBroker:
    """Thread-safe pub/sub broker mapping conversation IDs to active WebSocket clients."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rooms: dict[int, set[Any]] = {}

    def subscribe(self, conv_id: int, ws: Any) -> None:
        """Register a WebSocket client to receive broadcasts for conv_id."""
        with self._lock:
            self._rooms.setdefault(conv_id, set()).add(ws)

    def unsubscribe(self, conv_id: int, ws: Any) -> None:
        """Remove a WebSocket client from conv_id."""
        with self._lock:
            clients = self._rooms.get(conv_id)
            if not clients:
                return
            clients.discard(ws)
            if not clients:
                self._rooms.pop(conv_id, None)

    def broadcast(self, conv_id: int, payload: dict[str, Any]) -> None:
        """Send JSON payload to all active WebSocket clients in conv_id."""
        with self._lock:
            clients = list(self._rooms.get(conv_id, ()))

        if not clients:
            return

        raw = json.dumps(payload)
        dead: list[Any] = []
        for ws in clients:
            try:
                ws.send(raw)
            except Exception:
                dead.append(ws)

        if dead:
            with self._lock:
                room = self._rooms.get(conv_id)
                if room:
                    for ws in dead:
                        room.discard(ws)
                    if not room:
                        self._rooms.pop(conv_id, None)


room_broker = RoomBroker()
