from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# CORS middleware - Allow all origins for development/production flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:2013",
        "http://localhost:2014",
        "http://127.0.0.1:2013",
        "http://127.0.0.1:2014",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://213.230.97.43:2013",
        "http://213.230.97.43:2014",
        "https://213.230.97.43:2013",
        "https://213.230.97.43:2014",
    ],
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
        "university": settings.UNIVERSITY_NAME,
        "university_short": settings.UNIVERSITY_SHORT_NAME,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/info")
def system_info():
    """Get system and university information."""
    return {
        "university_name": settings.UNIVERSITY_NAME,
        "university_short_name": settings.UNIVERSITY_SHORT_NAME,
        "api_version": "1.0.0",
        "hemis_api_url": settings.EXTERNAL_API_URL,
    }


@app.get("/ws-stats")
def websocket_stats():
    """Get WebSocket connection statistics for monitoring."""
    from .services.websocket_manager import manager
    import psutil
    import os

    # Get process info
    process = psutil.Process(os.getpid())

    # Get connection stats
    stats = manager.get_connection_stats()

    # Add system resource info
    stats["system"] = {
        "cpu_percent": process.cpu_percent(interval=0.1),
        "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
        "open_files": len(process.open_files()),
        "threads": process.num_threads(),
        "connections": len(process.connections()),
    }

    return stats


# Serve frontend static files (for production)
frontend_dist = Path(__file__).parent.parent.parent / "web" / "dist"
if frontend_dist.exists():
    # Mount static assets (JS, CSS, etc.)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Catch-all route to serve index.html for client-side routing
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve frontend for all non-API routes (enables client-side routing)"""
        # List of backend API route prefixes (NOT frontend routes)
        api_prefixes = (
            "api/",
            "auth/",
            "events/",
            "candidates/",
            "event-management/",
            "ws/",
            "docs",
            "openapi.json",
            "health",
            "uploads/",
            "redoc"
        )

        # Skip only backend API routes, NOT frontend routes
        # display/ prefix is used by BOTH backend API (/display/{event_id}/current)
        # and frontend routes (/display/{link})
        # We need to distinguish: API uses /display/{number} while frontend uses /display/{uuid}

        if full_path.startswith(api_prefixes):
            # Let FastAPI handle API routes normally (will return 404 if not found)
            return None

        # Special handling for /display/ routes
        if full_path.startswith("display/"):
            # Check if it's an API route (format: display/{number}/...)
            parts = full_path.split("/")
            if len(parts) >= 3 and parts[1].isdigit():
                # This is backend API: /display/123/current or /display/123/set-current
                return None
            # Otherwise it's frontend route: /display/{uuid}
            # Fall through to serve index.html

        # Serve index.html for frontend routes (vote, display, admin, etc.)
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

        return {"error": "Frontend not built. Run 'npm run build' in web directory."}
