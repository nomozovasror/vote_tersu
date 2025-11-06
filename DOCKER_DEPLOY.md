# Docker Deployment Guide

## 🐳 Docker bilan Ishga Tushirish

### Tuzatilgan Muammo:

**Nginx konfiguratsiyasida display route muammosi:**
- ❌ Eski: `/display` bilan boshlangan BARCHA route'lar backend'ga yuborilardi
- ✅ Yangi: Faqat `/display/{number}/...` backend'ga, `/display/{uuid}` frontend'ga

### Arxitektura:

```
┌─────────────────────────────────────────────┐
│         Client Browser                       │
│  http://213.230.97.43:2013                  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│    voting_web (Nginx - Port 2013)           │
├─────────────────────────────────────────────┤
│  Frontend Routes (index.html):              │
│    /admin/*                                 │
│    /vote/{uuid}                             │
│    /display/{uuid}         ← FIXED!         │
│                                              │
│  Backend API Proxy:                         │
│    /auth/*        → api:8000                │
│    /events/*      → api:8000                │
│    /candidates/*  → api:8000                │
│    /display/123/* → api:8000 (number only)  │
│    /ws/*          → api:8000                │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│   voting_api (FastAPI - Port 2014)          │
│   Internal: api:8000                        │
│   External: localhost:2014                  │
└─────────────────────────────────────────────┘
```

---

## 🚀 Deployment

### 1. Frontend'ni Rebuild Qilish

```bash
cd /Users/asrornomozov/Desktop/vote_app/web
npm run build
```

### 2. Docker Containers'ni Rebuild va Restart

```bash
cd /Users/asrornomozov/Desktop/vote_app

# Stop running containers
docker-compose down

# Rebuild images (web container uchun - nginx.conf o'zgardi)
docker-compose build web

# Start all services
docker-compose up -d

# Yoki bitta komanda bilan:
docker-compose up -d --build
```

### 3. Logs Ko'rish

```bash
# Barcha logs
docker-compose logs -f

# Faqat web (nginx)
docker-compose logs -f web

# Faqat api (fastapi)
docker-compose logs -f api
```

### 4. Status Tekshirish

```bash
# Containers ishlayaptimi?
docker-compose ps

# Nginx config test
docker exec voting_web nginx -t

# Nginx reload (agar kerak bo'lsa)
docker exec voting_web nginx -s reload
```

---

## 🧪 Testing

### Health Checks:

```bash
# Frontend (nginx)
curl http://localhost:2013

# Backend (fastapi)
curl http://localhost:2014/health
# {"status":"healthy"}

# Backend via nginx proxy
curl http://localhost:2013/health
# {"status":"healthy"}
```

### Display Page Test:

```bash
# Frontend route (index.html'ni qaytarishi kerak)
curl -I http://localhost:2013/display/0a2350c1
# HTTP/1.1 200 OK
# Content-Type: text/html

# Backend API route (JSON qaytarishi kerak)
curl http://localhost:2013/display/123/current
# {"event_id":123,"current_candidate":null,...}
```

### Browser Test:

1. Admin: `http://localhost:2013/admin/login` ✅
2. Vote: `http://localhost:2013/vote/{link}` ✅
3. Display: `http://localhost:2013/display/{link}` ✅ **FIXED!**

---

## 🔍 Nginx Routing Logic

### Yangi Konfiguratsiya:

```nginx
# 1. Backend API: /display/{number}/...
location ~ ^/display/[0-9]+/ {
    proxy_pass http://api:8000;
}

# 2. Other backend APIs
location ~ ^/(auth|api|candidates|events|...) {
    proxy_pass http://api:8000;
}

# 3. Frontend routes (catch-all)
location / {
    try_files $uri $uri/ /index.html;
}
```

### Route Examples:

| URL | Handled By | Reason |
|-----|------------|--------|
| `/display/0a2350c1` | Frontend | UUID (not a number) |
| `/display/abc123` | Frontend | Alphanumeric |
| `/display/123/current` | Backend | Starts with number |
| `/display/456/set-current` | Backend | Starts with number |
| `/vote/xyz789` | Frontend | Catch-all |
| `/admin/dashboard` | Frontend | Catch-all |
| `/auth/login` | Backend | Explicit proxy |
| `/events/1` | Backend | Explicit proxy |

---

## 🛠️ Troubleshooting

### Display page 404:

```bash
# 1. Check nginx config
docker exec voting_web cat /etc/nginx/conf.d/default.conf

# 2. Check frontend build
docker exec voting_web ls -la /usr/share/nginx/html/

# 3. Rebuild web container
docker-compose build web
docker-compose up -d web
```

### API not responding:

```bash
# 1. Check API logs
docker-compose logs api

# 2. Check API health
curl http://localhost:2014/health

# 3. Restart API
docker-compose restart api
```

### Nginx errors:

```bash
# 1. Check nginx logs
docker-compose logs web

# 2. Test nginx config
docker exec voting_web nginx -t

# 3. Reload nginx
docker exec voting_web nginx -s reload
```

---

## 📝 Environment Variables

Create `.env` file in root directory:

```env
# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# JWT secret
SECRET_KEY=your-super-secret-key-change-this-in-production

# External API
EXTERNAL_API_TOKEN=your-tersu-api-token
```

---

## 🔄 Update/Redeploy

```bash
cd /Users/asrornomozov/Desktop/vote_app

# 1. Pull changes (if using git)
git pull

# 2. Rebuild frontend
cd web && npm run build && cd ..

# 3. Rebuild and restart containers
docker-compose up -d --build

# 4. Check logs
docker-compose logs -f
```

---

## 🗑️ Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes database!)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

---

## 📊 Monitoring

### Container stats:

```bash
docker stats voting_web voting_api
```

### Disk usage:

```bash
docker system df
```

### Network inspection:

```bash
docker network inspect vote_app_voting-network
```

---

## ✅ Post-Deployment Checklist

- [ ] Frontend build qilingan (`web/dist/` mavjud)
- [ ] Nginx config tuzatilgan (`display` routing)
- [ ] Docker containers rebuild qilingan
- [ ] Containers ishlamoqda (`docker-compose ps`)
- [ ] Health check muvaffaqiyatli (`/health`)
- [ ] Display page ochilmoqda (`/display/{link}`)
- [ ] WebSocket ishlayapti (`/ws/*`)
- [ ] Admin panel ochilmoqda (`/admin/login`)

---

## 🎯 HOZIR BAJARISH KERAK:

```bash
cd /Users/asrornomozov/Desktop/vote_app

# 1. Frontend rebuild (agar qilinmagan bo'lsa)
cd web && npm run build && cd ..

# 2. Docker containers restart
docker-compose down
docker-compose up -d --build

# 3. Logs tekshirish
docker-compose logs -f

# 4. Test qiling
curl http://localhost:2013/display/test123
# HTML qaytishi kerak (index.html)
```

**Display page endi ishlaydi!** 🎉
