from typing import Dict, List
from fastapi import WebSocket
import json


class ConnectionManager:
    def __init__(self):
        # event_link -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # display connections
        self.display_connections: Dict[str, List[WebSocket]] = {}

    async def connect_vote(self, websocket: WebSocket, event_link: str):
        await websocket.accept()
        if event_link not in self.active_connections:
            self.active_connections[event_link] = []
        self.active_connections[event_link].append(websocket)

    def disconnect_vote(self, websocket: WebSocket, event_link: str):
        if event_link in self.active_connections:
            if websocket in self.active_connections[event_link]:
                self.active_connections[event_link].remove(websocket)

    async def broadcast_vote(self, event_link: str, message: dict):
        if event_link in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[event_link]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.append(connection)

            # Remove dead connections
            for dead in dead_connections:
                self.active_connections[event_link].remove(dead)

    async def connect_display(self, websocket: WebSocket, event_link: str):
        await websocket.accept()
        if event_link not in self.display_connections:
            self.display_connections[event_link] = []
        self.display_connections[event_link].append(websocket)

    def disconnect_display(self, websocket: WebSocket, event_link: str):
        if event_link in self.display_connections:
            if websocket in self.display_connections[event_link]:
                self.display_connections[event_link].remove(websocket)

    async def broadcast_display(self, event_link: str, message: dict):
        if event_link in self.display_connections:
            dead_connections = []
            for connection in self.display_connections[event_link]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.append(connection)

            # Remove dead connections
            for dead in dead_connections:
                self.display_connections[event_link].remove(dead)


manager = ConnectionManager()
