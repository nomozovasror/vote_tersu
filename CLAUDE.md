# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-time voting system with FastAPI backend and React frontend. Features WebSocket support for live voting updates, admin panel for event management, and a display screen for showing candidates to audiences.

## Key Technologies

- **Backend**: FastAPI + SQLAlchemy + SQLite + WebSocket
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Auth**: JWT (admin only)
- **Real-time**: WebSocket connections for voting and display updates

## Development Commands

### Running the Application

**Docker (Recommended):**
```bash
# Build and start services
docker-compose up --build

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

**Manual Setup:**

Backend (from `api/` directory):
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m app.init_db

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (from `web/` directory):
```bash
# Install dependencies
npm install

# Create environment file
echo "VITE_API_URL=http://localhost:8000" > .env

# Run dev server
npm run dev

# Build for production
npm run build
```

### Database Operations

```bash
# Initialize/reset database
cd api
python -m app.init_db

# Delete and recreate database
rm -rf ../data/voting.db
python -m app.init_db
```

### Testing

```bash
# Test API endpoints
python test_api.py
```

## Architecture

### Backend Structure (`api/app/`)

**Core Components:**
- `core/config.py` - Environment configuration using pydantic-settings
- `core/security.py` - JWT token creation/validation, password hashing
- `core/database.py` - SQLAlchemy setup, session management, and lightweight schema migrations via `ensure_schema()`
- `core/dependencies.py` - FastAPI dependency injection (auth, database)

**Models (`models/`):**
- `admin.py` - AdminUser model (JWT authentication)
- `candidate.py` - Candidate model (synced from external API or manual entry)
- `event.py` - Event and EventCandidate models (voting events and candidate relationships)
- `vote.py` - Vote model (tracks IP-based voting)
- `display.py` - DisplayState model (controls what's shown on display screen)

**Routes (`routes/`):**
- `auth.py` - POST /auth/login, GET /auth/me
- `candidates.py` - Candidate CRUD, sync from external API
- `events.py` - Event CRUD, public event info via link
- `event_management.py` - Start/stop events, get results
- `display.py` - Set and get display state for events
- `websocket.py` - WebSocket endpoints for voting and display updates

**Services (`services/`):**
- `websocket_manager.py` - ConnectionManager class handles WebSocket connections and broadcasts for both voting and display channels

**Key Files:**
- `main.py` - FastAPI app initialization, CORS, router registration
- `init_db.py` - Database initialization script, creates admin user

### Frontend Structure (`web/src/`)

**Pages:**
- `Login.tsx` - Admin authentication
- `Dashboard.tsx` - Event list, create events, sync candidates
- `CandidatesManage.tsx` - Manage candidate list
- `EventManage.tsx` - Control specific event (start/stop, display control, results, **grouping candidates**)
- `VotePage.tsx` - Public voting interface with real-time updates (supports grouped candidate selection)
- `DisplayPage.tsx` - Large screen display with countdown timer

**Routing:**
- `/admin/login` - Admin login
- `/admin/dashboard` - Main admin interface
- `/admin/candidates` - Candidate management
- `/admin/event/:id` - Event management (includes group assignment)
- `/vote/:link` - Sequential voting page (grouped or standard voting)
- `/display/:link` - Display screen (for audiences)

### WebSocket Architecture

**Two separate WebSocket channels:**

1. **Voting Channel** (`/ws/vote/{link}`):
   - Receives vote submissions from users
   - Broadcasts real-time vote tallies to all connected voters
   - Handles IP-based duplicate vote prevention

2. **Display Channel** (`/ws/display/{link}`):
   - Receives admin commands to update display state
   - Broadcasts candidate info and countdown timer to display screens
   - Independent timing from voting events

**ConnectionManager** (`services/websocket_manager.py`):
- Maintains separate connection pools for voting and display
- Handles connection lifecycle (connect, disconnect, broadcast)
- Cleans up dead connections automatically

### Database Schema

**Key Relationships:**
- Event → EventCandidate (many-to-many through join table)
- EventCandidate → Candidate (foreign key)
- Vote → Event + Candidate (records individual votes)
- DisplayState → Event + Candidate (one per event)

**Important Fields:**
- Event.link - UUID for public access
- Event.status - Enum: 'pending', 'active', 'finished'
- Vote.ip_address - For preventing duplicate votes
- EventCandidate.timer_started_at - Tracks when display timer started for this candidate
- Candidate.which_position - Position/title of candidate

**Schema Migrations:**
The `ensure_schema()` function in `core/database.py` handles lightweight migrations:
- Adds `timer_started_at` column to event_candidates if missing
- Adds `which_position` column to candidates if missing
- Runs automatically on application startup

### External API Integration

**Candidate Sync:**
- Endpoint: `https://student.tersu.uz/rest/v1/data/employee-list`
- Requires: `EXTERNAL_API_TOKEN` environment variable
- Syncs employee data into candidate records
- Marks synced candidates with `from_api=True`

## Configuration

Environment variables (`.env` file):

```env
DATABASE_URL=sqlite:///./data/voting.db
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
EXTERNAL_API_URL=https://student.tersu.uz/rest/v1/data/employee-list
EXTERNAL_API_TOKEN=your-token
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
FRONTEND_URL=http://localhost:5173
```

## Voting System

### Sequential Voting with Grouping (`/vote/:link`)

The application uses sequential voting where candidates are shown one at a time with timer-based voting.

**Key Features:**
- Real-time WebSocket updates
- Timer-controlled voting sessions
- Supports **grouped candidates** for competitive positions

**Grouped Voting:**
When multiple candidates compete for the same position (e.g., 4 candidates for "Rektor"), they can be grouped together using the `candidate_group` field on EventCandidate.

- **How it works:**
  1. Admin assigns candidates to a group (e.g., "Rektor-Group-1")
  2. When that group's turn comes, ALL candidates in the group are displayed
  3. Voter selects ONE candidate from the group
  4. Selected candidate gets "yes" vote
  5. Other candidates in the group automatically get "no" votes

- **Backend logic:**
  - EventCandidate model has `candidate_group` field (nullable string)
  - WebSocket endpoint accepts `candidate_id` parameter for group voting
  - Auto-voting logic assigns "no" votes to unselected group members

**Standard (Non-Grouped) Voting:**
- Single candidate shown at a time
- Voter chooses Yes/No/Neutral
- No auto-voting for non-grouped candidates

## Common Tasks

### Setting Up Grouped Voting

To create a grouped voting scenario (e.g., 4 candidates competing for one position):

1. **Add candidates to event** - Use EventManage page to add all competing candidates
2. **Assign group** (Backend API):
   ```python
   POST /event-management/{event_id}/set-group
   {
     "event_candidate_ids": [1, 2, 3, 4],
     "group_name": "Rektor-Group-1"
   }
   ```
3. **Start event** - When the first candidate in the group's turn comes, all group members will be displayed
4. **Voters select one** - Voters see all candidates and choose one
5. **Results** - Selected candidate gets "yes", others get "no"

**Important:**
- Groups must have at least 2 candidates
- Group candidates can be in any position in the sequence
- Only group-based auto-voting is supported (no position-based fallback)
- Frontend automatically detects groups via `related_candidates` array

### Adding New Endpoints

1. Create route function in appropriate file under `api/app/routes/`
2. Use dependency injection from `core/dependencies.py` for auth and database
3. Register router in `api/app/main.py` if creating new route file
4. Update frontend API calls accordingly

### Modifying Database Schema

1. Update model in `api/app/models/`
2. Add migration logic to `ensure_schema()` in `core/database.py`
3. Test with fresh database: `rm data/voting.db && python -m app.init_db`

### Adding WebSocket Features

1. Extend ConnectionManager in `services/websocket_manager.py` if needed
2. Add WebSocket endpoint in `routes/websocket.py`
3. Update frontend to establish connection and handle messages
4. Test message flow: client → server → broadcast → all clients

### Debugging WebSocket Issues

- Check browser console for WebSocket connection errors
- Verify CORS settings in `main.py` allow WebSocket origins
- Inspect ConnectionManager state for active connections
- Look for dead connection cleanup in logs

## Production Considerations

- Change `SECRET_KEY` and `ADMIN_PASSWORD` in production
- Consider migrating from SQLite to PostgreSQL for better concurrency
- Set up proper HTTPS/WSS for WebSocket connections
- Configure proper CORS origins (remove wildcard if present)
- Set up logging and monitoring for WebSocket connections

## Default Credentials

- Username: `admin`
- Password: `admin123`

Change these immediately in production by updating the `.env` file and reinitializing the database.
