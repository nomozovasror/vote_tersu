from typing import Dict, List
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
        connections = self.active_connections[event_link].copy()  # Copy to avoid modification during iteration

        # Use asyncio.gather for concurrent sending with timeout
        async def send_with_timeout(connection: WebSocket):
            try:
                await asyncio.wait_for(connection.send_json(message), timeout=5.0)
                return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout sending to connection in {event_link}")
                return connection
            except Exception as e:
                logger.debug(f"Error sending to connection in {event_link}: {type(e).__name__}")
                return connection

        # Send to all connections concurrently
        results = await asyncio.gather(*[send_with_timeout(conn) for conn in connections], return_exceptions=True)

        # Collect dead connections
        for result in results:
            if isinstance(result, WebSocket):
                dead_connections.append(result)

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
        connections = self.display_connections[event_link].copy()  # Copy to avoid modification during iteration

        # Use asyncio.gather for concurrent sending with timeout
        async def send_with_timeout(connection: WebSocket):
            try:
                await asyncio.wait_for(connection.send_json(message), timeout=5.0)
                return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout sending to display connection in {event_link}")
                return connection
            except Exception as e:
                logger.debug(f"Error sending to display connection in {event_link}: {type(e).__name__}")
                return connection

        # Send to all connections concurrently
        results = await asyncio.gather(*[send_with_timeout(conn) for conn in connections], return_exceptions=True)

        # Collect dead connections
        for result in results:
            if isinstance(result, WebSocket):
                dead_connections.append(result)

        # Remove dead connections
        for dead in dead_connections:
            if dead in self.display_connections.get(event_link, []):
                self.display_connections[event_link].remove(dead)

        if dead_connections:
            logger.info(f"Removed {len(dead_connections)} dead display connections from {event_link}")


manager = ConnectionManager()
