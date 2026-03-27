from typing import Dict, List, Optional, Callable, Awaitable
from fastapi import WebSocket
import json
import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # event_link -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # display connections
        self.display_connections: Dict[str, List[WebSocket]] = {}
        # Connection limits from environment variables
        self.max_connections_per_event = int(os.getenv("MAX_CONNECTIONS_PER_EVENT", "500"))
        self.max_total_connections = int(os.getenv("MAX_TOTAL_CONNECTIONS", "2000"))
        # Timer tasks: event_link -> asyncio.Task
        self._timer_tasks: Dict[str, asyncio.Task] = {}

    def schedule_timer_expiry(
        self,
        event_link: str,
        duration_sec: float,
        on_expire: Callable[[], Awaitable[None]],
    ):
        """Schedule a background task that fires when the voting timer expires."""
        # Cancel any existing timer for this event
        self.cancel_timer(event_link)

        async def _wait_and_fire():
            try:
                await asyncio.sleep(duration_sec)
                await on_expire()
            except asyncio.CancelledError:
                logger.info(f"Timer cancelled for {event_link}")
            except Exception as e:
                logger.error(f"Timer expiry error for {event_link}: {e}")
            finally:
                self._timer_tasks.pop(event_link, None)

        task = asyncio.create_task(_wait_and_fire())
        self._timer_tasks[event_link] = task
        logger.info(f"Timer scheduled for {event_link}: {duration_sec}s")

    def cancel_timer(self, event_link: str):
        """Cancel a running timer for an event."""
        task = self._timer_tasks.pop(event_link, None)
        if task and not task.done():
            task.cancel()
            logger.info(f"Timer cancelled for {event_link}")

    def get_total_vote_connections(self) -> int:
        """Get total number of active vote connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_total_display_connections(self) -> int:
        """Get total number of active display connections."""
        return sum(len(conns) for conns in self.display_connections.values())

    def get_connection_stats(self) -> dict:
        """Get connection statistics for monitoring."""
        return {
            "total_vote_connections": self.get_total_vote_connections(),
            "total_display_connections": self.get_total_display_connections(),
            "events_with_vote_connections": len(self.active_connections),
            "events_with_display_connections": len(self.display_connections),
        }

    async def connect_vote(self, websocket: WebSocket, event_link: str):
        # Check connection limits
        total_connections = self.get_total_vote_connections() + self.get_total_display_connections()
        if total_connections >= self.max_total_connections:
            logger.warning(f"Max total connections reached: {total_connections}")
            await websocket.close(code=1013, reason="Server overloaded")
            return

        if event_link in self.active_connections:
            if len(self.active_connections[event_link]) >= self.max_connections_per_event:
                logger.warning(f"Max connections per event reached for {event_link}")
                await websocket.close(code=1013, reason="Event connection limit reached")
                return

        await websocket.accept()
        if event_link not in self.active_connections:
            self.active_connections[event_link] = []
        self.active_connections[event_link].append(websocket)

        logger.info(f"Vote connection added for {event_link}. Total: {len(self.active_connections[event_link])}")

    def disconnect_vote(self, websocket: WebSocket, event_link: str):
        if event_link in self.active_connections:
            if websocket in self.active_connections[event_link]:
                self.active_connections[event_link].remove(websocket)
                logger.info(f"Vote connection removed for {event_link}. Remaining: {len(self.active_connections[event_link])}")

            # Clean up empty event lists
            if not self.active_connections[event_link]:
                del self.active_connections[event_link]

    async def broadcast_vote(self, event_link: str, message: dict):
        if event_link not in self.active_connections:
            return

        dead_connections = []
        connections = self.active_connections[event_link].copy()

        # Serialize message once instead of per-connection
        message_text = json.dumps(message)

        # Send in batches to avoid blocking event loop
        batch_size = 50
        for i in range(0, len(connections), batch_size):
            batch = connections[i:i + batch_size]

            async def send_one(conn: WebSocket):
                try:
                    await asyncio.wait_for(conn.send_text(message_text), timeout=5.0)
                    return None
                except Exception:
                    return conn

            results = await asyncio.gather(*[send_one(c) for c in batch], return_exceptions=True)

            for result in results:
                if isinstance(result, WebSocket):
                    dead_connections.append(result)

            # Yield control to event loop between batches
            if i + batch_size < len(connections):
                await asyncio.sleep(0)

        # Remove dead connections
        for dead in dead_connections:
            if dead in self.active_connections.get(event_link, []):
                self.active_connections[event_link].remove(dead)

        if dead_connections:
            logger.info(f"Removed {len(dead_connections)} dead vote connections from {event_link}")

    async def connect_display(self, websocket: WebSocket, event_link: str):
        # Check connection limits
        total_connections = self.get_total_vote_connections() + self.get_total_display_connections()
        if total_connections >= self.max_total_connections:
            logger.warning(f"Max total connections reached: {total_connections}")
            await websocket.close(code=1013, reason="Server overloaded")
            return

        await websocket.accept()
        if event_link not in self.display_connections:
            self.display_connections[event_link] = []
        self.display_connections[event_link].append(websocket)

        logger.info(f"Display connection added for {event_link}. Total: {len(self.display_connections[event_link])}")

    def disconnect_display(self, websocket: WebSocket, event_link: str):
        if event_link in self.display_connections:
            if websocket in self.display_connections[event_link]:
                self.display_connections[event_link].remove(websocket)
                logger.info(f"Display connection removed for {event_link}. Remaining: {len(self.display_connections[event_link])}")

            # Clean up empty event lists
            if not self.display_connections[event_link]:
                del self.display_connections[event_link]

    async def broadcast_display(self, event_link: str, message: dict):
        if event_link not in self.display_connections:
            return

        dead_connections = []
        connections = self.display_connections[event_link].copy()

        message_text = json.dumps(message)

        batch_size = 50
        for i in range(0, len(connections), batch_size):
            batch = connections[i:i + batch_size]

            async def send_one(conn: WebSocket):
                try:
                    await asyncio.wait_for(conn.send_text(message_text), timeout=5.0)
                    return None
                except Exception:
                    return conn

            results = await asyncio.gather(*[send_one(c) for c in batch], return_exceptions=True)

            for result in results:
                if isinstance(result, WebSocket):
                    dead_connections.append(result)

            if i + batch_size < len(connections):
                await asyncio.sleep(0)

        # Remove dead connections
        for dead in dead_connections:
            if dead in self.display_connections.get(event_link, []):
                self.display_connections[event_link].remove(dead)

        if dead_connections:
            logger.info(f"Removed {len(dead_connections)} dead display connections from {event_link}")


manager = ConnectionManager()
