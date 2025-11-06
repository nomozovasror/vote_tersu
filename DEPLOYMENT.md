# Production Deployment Guide

## Production Muhitda Ishga Tushirish

### 1. Backend Deployment (Port 2014)

```bash
cd /Users/asrornomozov/Desktop/vote_app/api

# Virtual environment yaratish (birinchi marta)
python3 -m venv venv
source venv/bin/activate

# Dependencies o'rnatish
pip install -r requirements.txt

# Database yaratish (birinchi marta)
python -m app.init_db

# Backend ishga tushirish
uvicorn app.main:app --host 0.0.0.0 --port 2014
```

Production uchun Gunicorn bilan:
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:2014
```

### 2. Frontend Deployment (Port 2013)

**A variant: Backend orqali serve qilish (tavsiya etiladi)**

Frontend allaqachon backend `main.py` da serve qilinadi:
- Backend run qilganingizda frontend avtomatik serve bo'ladi
- URL: `http://213.230.97.43:2014/`

**B variant: Alohida frontend server (agar kerak bo'lsa)**

```bash
cd /Users/asrornomozov/Desktop/vote_app/web

# Dependencies o'rnatish (birinchi marta)
npm install

# Production build
npm run build

# Nginx yoki serve bilan serve qilish
npm install -g serve
serve -s dist -l 2013
```

### 3. Environment Variables

**Backend** (`api/.env`):
```env
SECRET_KEY=your-super-secret-production-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
BACKEND_URL=http://213.230.97.43:2014
EXTERNAL_API_URL=https://student.tersu.uz/rest/v1/data/employee-list
EXTERNAL_API_TOKEN=your-token-here
```

**Frontend**: API URL avtomatik aniqlash
- Development: `http://localhost:2014`
- Production: `http://<current-hostname>:2014`

### 4. Systemd Service (Linux/Ubuntu)

**Backend service** (`/etc/systemd/system/voting-backend.service`):
```ini
[Unit]
Description=Voting System Backend
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/Users/asrornomozov/Desktop/vote_app/api
Environment="PATH=/Users/asrornomozov/Desktop/vote_app/api/venv/bin"
ExecStart=/Users/asrornomozov/Desktop/vote_app/api/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:2014
Restart=always

[Install]
WantedBy=multi-user.target
```

Service'ni yoqish:
```bash
sudo systemctl enable voting-backend
sudo systemctl start voting-backend
sudo systemctl status voting-backend
```

### 5. Nginx Reverse Proxy (ixtiyoriy)

**Nginx konfiguratsiyasi** (`/etc/nginx/sites-available/voting`):
```nginx
server {
    listen 80;
    server_name 213.230.97.43 your-domain.com;

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:2014;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:2014;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:2014;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Nginx'ni qayta yuklash:
```bash
sudo ln -s /etc/nginx/sites-available/voting /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Firewall sozlamalari

```bash
# UFW (Ubuntu)
sudo ufw allow 2013/tcp
sudo ufw allow 2014/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

### 7. SSL/HTTPS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 8. Deployment Checklist

- [ ] Backend `.env` fayli to'ldirilgan
- [ ] Database yaratilgan (`python -m app.init_db`)
- [ ] Frontend build qilingan (`npm run build`)
- [ ] Backend port 2014 da ishlamoqda
- [ ] CORS sozlamalari to'g'ri
- [ ] Firewall portlari ochiq
- [ ] Systemd service yoqilgan (production uchun)

### 9. Yangilanishlarni Deploy qilish

```bash
# 1. Git pull (agar git ishlatilsa)
cd /Users/asrornomozov/Desktop/vote_app
git pull

# 2. Backend yangilash
cd api
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart voting-backend

# 3. Frontend rebuild
cd ../web
npm install
npm run build

# 4. Restart services
sudo systemctl restart voting-backend
```

### 10. Logs va Monitoring

```bash
# Backend logs
sudo journalctl -u voting-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Application logs
cd /Users/asrornomozov/Desktop/vote_app/api
tail -f app.log
```

### 11. Troubleshooting

**Backend ishlamayapti:**
```bash
sudo systemctl status voting-backend
sudo journalctl -u voting-backend -n 50
```

**CORS xatolari:**
- `api/app/main.py` da `allow_origins` ro'yxatini tekshiring
- Production IP/domen qo'shilganligiga ishonch hosil qiling

**Frontend 404:**
- Frontend build qilinganligini tekshiring: `ls web/dist/`
- Backend'da frontend serve sozlamalari to'g'ri ekanligini tekshiring

**WebSocket ulanmayapti:**
- Port 2014 ochiq ekanligini tekshiring
- Nginx orqali ishlatilsa, WebSocket proxy sozlamalari to'g'ri ekanligini tekshiring

### 12. Hozirgi Sozlamalar

**Server:** `213.230.97.43`

**Portlar:**
- Frontend: 2013 (yoki backend orqali)
- Backend: 2014

**URLs:**
- Admin: `http://213.230.97.43:2014/admin/login`
- Vote: `http://213.230.97.43:2014/vote/{link}`
- Display: `http://213.230.97.43:2014/display/{link}`
- API: `http://213.230.97.43:2014/docs`

**Smart API Detection:**
Frontend avtomatik ravishda to'g'ri API URL'ni aniqlaydi:
- `http://213.230.97.43:2013` dan ochilsa → `http://213.230.97.43:2014` API
- `http://localhost:2013` dan ochilsa → `http://localhost:2014` API
