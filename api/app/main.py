from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .core.config import settings
from .core.database import engine, Base, ensure_schema
from .routes import auth, candidates, events, display, websocket, event_management

# Create database tables and apply lightweight migrations
Base.metadata.create_all(bind=engine)
ensure_schema()

app = FastAPI(
    title="Real-Time Voting System API",
    description="FastAPI backend for real-time voting with WebSocket support",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:2013", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (uploads)
uploads_dir = Path("./data/uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(events.router)
app.include_router(event_management.router)
app.include_router(display.router)
app.include_router(websocket.router)


@app.get("/")
def root():
    return {
        "message": "Real-Time Voting System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
