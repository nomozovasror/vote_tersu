# Quick Deployment Guide - Port 2013

## 🚀 Production setup (Backend va Frontend bitta portda - 2013)

### 1. Backend'ni 2013 portda ishga tushirish

```bash
cd /Users/asrornomozov/Desktop/vote_app/api

# Virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Backend ishga tushirish (port 2013)
uvicorn app.main:app --host 0.0.0.0 --port 2013
```

### 2. Backend fonda ishlashi uchun (Production)

**Gunicorn bilan:**
```bash
cd /Users/asrornomozov/Desktop/vote_app/api
source venv/bin/activate
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:2013 --daemon
```

**nohup bilan:**
```bash
cd /Users/asrornomozov/Desktop/vote_app/api
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 2013 > ../backend.log 2>&1 &
```

**tmux bilan:**
```bash
tmux new -s voting
cd /Users/asrornomozov/Desktop/vote_app/api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 2013
# Ctrl+B, D - detach qilish
```

### 3. Yangilanishlarni Deploy qilish

```bash
# 1. Kod o'zgartirish
cd /Users/asrornomozov/Desktop/vote_app

# 2. Frontend rebuild
cd web
npm run build

# 3. Backend restart
cd ../api
# Agar nohup ishlatilgan bo'lsa:
pkill -f "uvicorn app.main:app"
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 2013 > ../backend.log 2>&1 &

# Yoki gunicorn:
pkill -f "gunicorn app.main:app"
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:2013 --daemon
```

### 4. Process'ni tekshirish

```bash
# Backend process topish
ps aux | grep uvicorn
ps aux | grep gunicorn

# Port tekshirish
netstat -tulpn | grep 2013
lsof -i :2013

# Log'larni ko'rish
tail -f /Users/asrornomozov/Desktop/vote_app/backend.log
```

### 5. Systemd Service (Production - tavsiya etiladi)

**Service yaratish:**
```bash
sudo nano /etc/systemd/system/voting.service
```

**Service konfiguratsiyasi:**
```ini
[Unit]
Description=Voting System (Backend + Frontend)
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/Users/asrornomozov/Desktop/vote_app/api
Environment="PATH=/Users/asrornomozov/Desktop/vote_app/api/venv/bin"
ExecStart=/Users/asrornomozov/Desktop/vote_app/api/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:2013
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Service boshqarish:**
```bash
# Service yoqish
sudo systemctl enable voting
sudo systemctl start voting

# Status tekshirish
sudo systemctl status voting

# Restart
sudo systemctl restart voting

# Stop
sudo systemctl stop voting

# Logs
sudo journalctl -u voting -f
```

### 6. URL'lar

Barcha quyidagi URL'lar **bitta port (2013)** orqali ishlaydi:

- **Admin Panel**: `http://213.230.97.43:2013/admin/login`
- **Dashboard**: `http://213.230.97.43:2013/admin/dashboard`
- **Vote Page**: `http://213.230.97.43:2013/vote/{link}`
- **Display Page**: `http://213.230.97.43:2013/display/{link}`
- **API Docs**: `http://213.230.97.43:2013/docs`
- **Health Check**: `http://213.230.97.43:2013/health`

### 7. Arxitektura

```
┌─────────────────────────────────────────────┐
│         Client Browser                       │
│  http://213.230.97.43:2013/*                │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│      FastAPI Backend (Port 2013)            │
├─────────────────────────────────────────────┤
│  ├─ /api/*          → API endpoints         │
│  ├─ /auth/*         → Authentication        │
│  ├─ /events/*       → Events API            │
│  ├─ /ws/*           → WebSocket             │
│  ├─ /assets/*       → Static files (CSS/JS) │
│  └─ /*              → Frontend (index.html) │
│                                              │
│  Frontend Routes (React Router):            │
│    /admin/login                             │
│    /admin/dashboard                         │
│    /vote/{link}                             │
│    /display/{link}                          │
└─────────────────────────────────────────────┘
```

### 8. Troubleshooting

**Display page 404:**
```bash
# Frontend build qilinganligini tekshiring
ls -la /Users/asrornomozov/Desktop/vote_app/web/dist/

# Backend restart
sudo systemctl restart voting
```

**API ulanmayapti:**
```bash
# Backend ishlab turibmi
curl http://localhost:2013/health

# Port ochiqmi
sudo ufw allow 2013/tcp
```

**CORS xatolari:**
```bash
# Browser console'da xatoni ko'ring
# api/app/main.py da CORS sozlamalarini tekshiring
```

### 9. Firewall

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 2013/tcp
sudo ufw reload

# firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=2013/tcp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 2013 -j ACCEPT
sudo iptables-save
```

### 10. Muhim Eslatmalar

1. **Backend 2013 portda ishlatilmoqda** (2014 emas!)
2. **Frontend backend orqali serve qilinadi** - alohida frontend server kerak emas
3. **Display route fix qilindi** - `/display/{uuid}` frontend, `/display/{id}/current` API
4. **Yangi build allaqachon qilingan** - faqat backend restart kerak

### 11. Hozir bajarish kerak:

```bash
# 1. Eski backend process'ni to'xtatish
pkill -f "uvicorn app.main:app"
pkill -f "gunicorn app.main:app"

# 2. Yangi backend ishga tushirish (port 2013)
cd /Users/asrornomozov/Desktop/vote_app/api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 2013

# Yoki fonda:
nohup uvicorn app.main:app --host 0.0.0.0 --port 2013 > ../backend.log 2>&1 &
```

**Test:**
```bash
# Health check
curl http://213.230.97.43:2013/health

# Browser'da oching:
http://213.230.97.43:2013/admin/login
http://213.230.97.43:2013/display/YOUR_LINK
```

✅ Tayyor!
