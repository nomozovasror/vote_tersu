# 🗳️ Real-Time Voting System

A full-stack real-time voting application with FastAPI backend and React frontend, featuring WebSocket support for live updates and a display screen for audiences.

## 🎯 Features

- **Admin Panel**: Manage events, candidates, and view live results
- **Real-time Voting**: Users can vote via unique links with WebSocket updates
- **Display Screen**: Large screen view with countdown timer for audiences
- **JWT Authentication**: Secure admin authentication
- **External API Integration**: Sync candidates from external API
- **IP-based Vote Prevention**: One vote per IP per event
- **Live Results**: Real-time vote tallies with percentages

## 🧱 Tech Stack

### Backend
- FastAPI
- SQLAlchemy (SQLite)
- WebSocket
- JWT Authentication
- Pydantic

### Frontend
- React + TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios

## 🚀 Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <your-repo>
cd vote_app
```

2. Create `.env` file (copy from `.env.example` and update):
```bash
cp .env.example .env
```

3. Build and run with Docker Compose:
```bash
docker-compose up --build
```

4. Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend

1. Create virtual environment:
```bash
cd api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize database:
```bash
python -m app.init_db
```

4. Run the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

1. Install dependencies:
```bash
cd web
npm install
```

2. Create `.env` file:
```bash
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. Run development server:
```bash
npm run dev
```

## 📖 Usage

### Admin Workflow

1. **Login**: Navigate to `/admin/login` (default: admin/admin123)
2. **Sync Candidates**: Click "Sync Candidates" to fetch from external API
3. **Create Event**:
   - Click "Create Event"
   - Enter event name and duration
   - Select candidates
4. **Start Event**: Click "Start Event" when ready
5. **Control Display**:
   - Select candidate and countdown duration
   - Click "Update Display" to show on display screen
6. **Monitor Results**: View live vote counts and percentages
7. **Stop Event**: Click "Stop Event" when finished

### Voter Workflow

1. Receive unique voting link: `/vote/<event-link>`
2. View candidates and current results
3. Click "Vote" button for chosen candidate
4. See real-time result updates

### Display Screen

1. Open display link: `/display/<event-link>`
2. Shows current candidate with:
   - Large countdown timer
   - Candidate photo and details
   - Current vote count
3. Click "Fullscreen" for better visibility

## 🔐 Default Credentials

- **Username**: admin
- **Password**: admin123

**⚠️ Change these in production!**

## 📡 API Endpoints

### Authentication
- `POST /auth/login` - Admin login
- `GET /auth/me` - Get current user

### Candidates
- `POST /candidates/sync-from-api` - Sync from external API
- `POST /candidates/manual` - Add manual candidate
- `GET /candidates` - List all candidates
- `PATCH /candidates/{id}` - Update candidate

### Events
- `POST /events` - Create event
- `GET /events` - List events (admin)
- `GET /events/by-link/{link}` - Get event by link (public)
- `POST /events/{id}/start` - Start event
- `POST /events/{id}/stop` - Stop event
- `GET /events/{id}/results` - Get results

### Display
- `POST /display/{event_id}/set-current` - Set display candidate
- `GET /display/{event_id}/current` - Get display state

### WebSocket
- `/ws/vote/{link}` - Voting WebSocket
- `/ws/display/{link}` - Display WebSocket

## 🗄️ Database Schema

- **AdminUser**: Admin authentication
- **Candidate**: Candidate information
- **Event**: Voting events
- **EventCandidate**: Event-candidate relationships
- **Vote**: Vote records
- **DisplayState**: Display screen state

## 🔧 Configuration

Edit `.env` file:

```env
# Database
DATABASE_URL=sqlite:///./data/voting.db

# JWT
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# External API
EXTERNAL_API_URL=https://student.tersu.uz/rest/v1/data/employee-list
EXTERNAL_API_TOKEN=your-token

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# CORS
FRONTEND_URL=http://localhost:5173
```

## 📦 Project Structure

```
vote_app/
├── api/                    # Backend (FastAPI)
│   ├── app/
│   │   ├── core/          # Config, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routes/        # API endpoints
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── web/                    # Frontend (React)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── types/         # TypeScript types
│   │   ├── utils/         # Utilities
│   │   └── main.tsx       # Entry point
│   ├── Dockerfile
│   └── package.json
├── data/                   # SQLite database
├── docker-compose.yml
├── .env
└── README.md
```

## 🐛 Troubleshooting

### WebSocket connection fails
- Check CORS settings in backend
- Ensure frontend is using correct WS URL
- Verify firewall allows WebSocket connections

### Can't login
- Verify database is initialized (`python -m app.init_db`)
- Check credentials in `.env`
- Clear browser localStorage

### Candidates not syncing
- Verify `EXTERNAL_API_URL` and `EXTERNAL_API_TOKEN` in `.env`
- Check API endpoint is accessible
- Review backend logs for errors

## 📝 License

MIT License

## 👨‍💻 Author

Your Name

## 🙏 Acknowledgments

Based on the requirements from the instructions.md file.
# vote_app
