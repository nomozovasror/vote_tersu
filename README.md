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

### Development (Local)

#### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <your-repo>
cd vote_app
```

2. Create `.env` files:
```bash
cp api/.env.example api/.env
cp web/.env.example web/.env
```

3. Build and run with Docker Compose:
```bash
docker-compose up --build
```

4. Access the application:
- Frontend: http://localhost:2015
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production Deployment

#### Quick Production Setup (Serverga deploy qilish)

1. Server'ga SSH orqali kirish:
```bash
ssh user@your-server-ip
```

2. Loyihani ko'chirish:
```bash
# Git orqali
git clone <your-repo> ~/vote_app
cd ~/vote_app

# YOKI scp orqali local kompyuterdan
scp -r vote_app/ user@your-server-ip:~/vote_app/
```

3. Quick start script'ni ishga tushirish:
```bash
cd ~/vote_app
chmod +x quick-start.sh
./quick-start.sh
```

Script avtomatik ravishda:
- ✅ Docker va Docker Compose o'rnatadi
- ✅ Environment fayllarini yaratadi
- ✅ Firewall sozlaydi (portlar: 2015, 8000)
- ✅ Container'larni build qiladi va ishga tushiradi
- ✅ Database'ni initsializatsiya qiladi

4. Browser'da oching:
- Frontend: `http://your-server-ip:2015`
- API: `http://your-server-ip:8000/docs`
- Admin: `http://your-server-ip:2015/admin/login`

5. **MUHIM**: `api/.env` faylida parolni o'zgartiring:
```bash
nano api/.env
# ADMIN_PASSWORD va EXTERNAL_API_TOKEN ni o'zgartiring
docker-compose restart
```

#### Batafsil Ko'rsatma

Production deployment haqida to'liq ma'lumot uchun [DEPLOY.md](DEPLOY.md) faylini o'qing.

#### Deployment Commandlar

```bash
# Loyihani ishga tushirish
./deploy.sh start

# Loglarni ko'rish
./deploy.sh logs

# Backup yaratish
./deploy.sh backup

# Yangilash
./deploy.sh update

# To'xtatish
./deploy.sh stop

# Status ko'rish
./deploy.sh status
```

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

## 🧪 Testing & Performance

### Stress Testing

Test the system with simulated concurrent users (no real users needed):

```bash
# Install test dependencies
pip install -r stress_test_requirements.txt

# Quick tests
./quick_test.sh <event-link> small   # 50 users
./quick_test.sh <event-link> medium  # 100 users
./quick_test.sh <event-link> large   # 200 users

# Custom test
python3 stress_test.py \
    --api http://localhost:2014 \
    --link <event-link> \
    --users 150 \
    --duration 60

# Ramp-up test (gradual load)
python3 stress_test.py \
    --api http://localhost:2014 \
    --link <event-link> \
    --mode ramp \
    --max-users 200 \
    --ramp-time 60
```

### Real-time Monitoring

Monitor system performance during tests:

```bash
# Start monitoring
python3 monitor.py --api http://localhost:2014

# Get current stats
curl http://localhost:2014/ws-stats
```

### Performance Benchmarks

**Current optimizations** (single worker + SQLite):
- ✅ 200-250 concurrent users
- ✅ 1000+ votes/minute
- ✅ 5-10ms latency
- ✅ ~800MB RAM usage

**For 500+ users**, see [PERFORMANCE.md](PERFORMANCE.md) for Redis pub/sub setup.

**Full documentation:**
- [STRESS_TEST_GUIDE.md](STRESS_TEST_GUIDE.md) - Complete testing guide
- [PERFORMANCE.md](PERFORMANCE.md) - Performance optimization & scaling
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Production deployment guide

## 🐛 Troubleshooting

### WebSocket connection fails
- Check CORS settings in backend
- Ensure frontend is using correct WS URL
- Verify firewall allows WebSocket connections
- Check file descriptor limits: `docker exec voting_api sh -c "ulimit -n"` (should be 65536)

### Only 30-40 users can connect
**This was a known issue - now fixed!**
- Solution: Docker ulimits, database session fixes, uvloop
- See [PERFORMANCE.md](PERFORMANCE.md) for details
- Redeploy with: `docker-compose build --no-cache && docker-compose up -d --force-recreate`

### Can't login
- Verify database is initialized (`python -m app.init_db`)
- Check credentials in `.env`
- Clear browser localStorage

### Candidates not syncing
- Verify `EXTERNAL_API_URL` and `EXTERNAL_API_TOKEN` in `.env`
- Check API endpoint is accessible
- Review backend logs for errors

### High CPU or Memory usage
- Check active connections: `curl http://localhost:2014/ws-stats`
- Monitor resources: `python3 monitor.py`
- Review [PERFORMANCE.md](PERFORMANCE.md) for optimization tips

## 📝 License

MIT License

## 👨‍💻 Author

Your Name

## 🙏 Acknowledgments

Based on the requirements from the instructions.md file.
# vote_app
