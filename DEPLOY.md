# Production Deployment Guide

Bu loyihani serverga deploy qilish uchun qadamma-qadam ko'rsatma.

## 1. Server Talablari

- **OS**: Ubuntu 20.04+ / Debian / CentOS
- **RAM**: Minimum 2GB (tavsiya: 4GB)
- **CPU**: 2 core
- **Disk**: 10GB
- **Portlar**: 2015 (Frontend), 8000 (API), 443 (HTTPS - optional)

## 2. Docker va Docker Compose O'rnatish

```bash
# Docker o'rnatish
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose o'rnatish
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Foydalanuvchiga docker ruxsati berish
sudo usermod -aG docker $USER

# Tizimni qayta yuklang yoki logout/login qiling
```

## 3. Loyihani Serverga Ko'chirish

```bash
# Server'ga SSH orqali kirish
ssh user@your-server-ip

# Loyiha uchun katalog yaratish
mkdir -p ~/vote_app
cd ~/vote_app

# Git orqali loyihani clone qilish (agar git repository bo'lsa)
git clone <your-repo-url> .

# YOKI scp orqali fayllarni ko'chirish (local kompyuterdan)
# Local kompyuterda:
scp -r /Users/asrornomozov/Desktop/vote_app/* user@your-server-ip:~/vote_app/
```

## 4. Environment Variables Sozlash

Production uchun `.env` faylini yarating:

```bash
cd ~/vote_app/api
nano .env
```

`.env` fayli mazmuni:

```env
# Database
DATABASE_URL=sqlite:///./data/voting.db

# Security - MUHIM: Bu qiymatlarni o'zgartiring!
SECRET_KEY=your-very-long-random-secret-key-here-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Admin credentials - MUHIM: Parolni o'zgartiring!
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-password-here

# External API
EXTERNAL_API_URL=https://student.tersu.uz/rest/v1/data/employee-list
EXTERNAL_API_TOKEN=your-api-token

# Backend URL - Server IP yoki domain
BACKEND_URL=http://your-server-ip:8000

# Frontend URL
FRONTEND_URL=http://your-server-ip:2015
```

Frontend uchun environment:

```bash
cd ~/vote_app/web
nano .env
```

```env
# API URL - Server IP yoki domain
VITE_API_URL=http://your-server-ip:8000
```

## 5. Production Docker Compose

`docker-compose.yml` faylini production uchun sozlang:

```bash
cd ~/vote_app
nano docker-compose.yml
```

Quyidagi konfiguratsiyani qo'shing:

```yaml
version: '3.8'

services:
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: voting_api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/voting.db
    env_file:
      - ./api/.env
    restart: unless-stopped
    networks:
      - voting-network

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    container_name: voting_web
    ports:
      - "2015:80"
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - voting-network

networks:
  voting-network:
    driver: bridge

volumes:
  data:
```

## 6. Firewall Sozlash (UFW)

```bash
# UFW o'rnatilganligini tekshirish
sudo apt update
sudo apt install ufw

# SSH portini ochish (disconnect bo'lmaslik uchun!)
sudo ufw allow 22/tcp

# Frontend va API portlarini ochish
sudo ufw allow 2015/tcp
sudo ufw allow 8000/tcp

# Agar HTTPS kerak bo'lsa
sudo ufw allow 443/tcp

# Firewall'ni yoqish
sudo ufw enable

# Statusni tekshirish
sudo ufw status
```

## 7. Loyihani Ishga Tushirish

```bash
cd ~/vote_app

# Docker image'larni build qilish va ishga tushirish
docker-compose up -d --build

# Loglarni ko'rish
docker-compose logs -f

# Statusni tekshirish
docker-compose ps
```

## 8. Database Initsializatsiya

```bash
# API container ichiga kirish
docker exec -it voting_api bash

# Database yaratish
python -m app.init_db

# Container'dan chiqish
exit
```

## 9. Tekshirish

Browser'da quyidagi URLlarni oching:

- **Frontend**: `http://your-server-ip:2015`
- **API**: `http://your-server-ip:8000/docs`
- **Admin Panel**: `http://your-server-ip:2015/admin/login`

## 10. Container Management

```bash
# Container'larni to'xtatish
docker-compose down

# Container'larni qayta ishga tushirish
docker-compose restart

# Loglarni ko'rish
docker-compose logs -f api
docker-compose logs -f web

# Container ichidagi fayllarni ko'rish
docker exec -it voting_api ls -la /app/data
```

## 11. Backup va Restore

### Backup

```bash
# Database backup
docker exec voting_api sqlite3 /app/data/voting.db ".backup '/app/data/backup_$(date +%Y%m%d_%H%M%S).db'"

# Yoki host'dan
cp ~/vote_app/data/voting.db ~/vote_app/data/backup_$(date +%Y%m%d_%H%M%S).db

# Butun data papkasini backup qilish
tar -czf vote_app_backup_$(date +%Y%m%d_%H%M%S).tar.gz ~/vote_app/data/
```

### Restore

```bash
# Database restore
docker exec voting_api cp /app/data/backup_YYYYMMDD_HHMMSS.db /app/data/voting.db

# Container'larni qayta ishga tushirish
docker-compose restart
```

## 12. Auto-start (System Reboot)

Docker'ni tizim boshlanganida avtomatik ishga tushirish:

```bash
# Docker service'ni enable qilish
sudo systemctl enable docker

# Docker compose service yaratish
sudo nano /etc/systemd/system/voting-app.service
```

Service fayli:

```ini
[Unit]
Description=Voting App
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/your-username/vote_app
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Service'ni enable qilish:

```bash
sudo systemctl daemon-reload
sudo systemctl enable voting-app.service
sudo systemctl start voting-app.service
```

## 13. Monitoring va Logs

```bash
# Real-time logs
docker-compose logs -f

# Faqat API logs
docker-compose logs -f api

# Oxirgi 100 ta log
docker-compose logs --tail=100

# Container resource usage
docker stats

# Disk usage
df -h
docker system df
```

## 14. Yangilanish (Update)

```bash
cd ~/vote_app

# Yangi kodlarni olish (git bo'lsa)
git pull

# Container'larni to'xtatish
docker-compose down

# Yangi image'larni build qilish
docker-compose up -d --build

# Loglarni tekshirish
docker-compose logs -f
```

## 15. Xavfsizlik Tavsiялari

1. **SECRET_KEY ni o'zgartiring** - Random 32+ belgili string
2. **ADMIN_PASSWORD ni o'zgartiring** - Kuchli parol
3. **SSH portini o'zgartiring** - Default 22 o'rniga
4. **SSH key authentication** qo'shing
5. **Fail2ban** o'rnating
6. **Regular backup** oling
7. **HTTPS (SSL)** qo'shing (quyidagi bonus bo'limga qarang)

## 16. Muammolarni Hal Qilish

### Container ishga tushmaydi
```bash
# Loglarni tekshirish
docker-compose logs api
docker-compose logs web

# Container'larni qayta build qilish
docker-compose down
docker-compose up -d --build --force-recreate
```

### Port band
```bash
# Qaysi process portni ishlatayotganini ko'rish
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :80

# Process'ni to'xtatish
sudo kill -9 <PID>
```

### Database xatolari
```bash
# Database'ni qayta yaratish
docker exec -it voting_api bash
rm /app/data/voting.db
python -m app.init_db
exit
docker-compose restart
```

## 17. BONUS: HTTPS (SSL) bilan Nginx Reverse Proxy

Agar domain'ingiz bo'lsa (masalan: vote.example.com):

### Nginx o'rnatish

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

### Nginx konfiguratsiya

```bash
sudo nano /etc/nginx/sites-available/voting-app
```

```nginx
server {
    listen 80;
    server_name vote.example.com;

    # Frontend
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Konfiguratsiyani yoqish
sudo ln -s /etc/nginx/sites-available/voting-app /etc/nginx/sites-enabled/

# Nginx'ni test qilish
sudo nginx -t

# Nginx'ni qayta yuklash
sudo systemctl reload nginx
```

### SSL sertifikat olish

```bash
sudo certbot --nginx -d vote.example.com
```

---

## Tez Start (Quick Start)

```bash
# 1. Server'ga kirish
ssh user@your-server-ip

# 2. Loyihani ko'chirish
mkdir ~/vote_app && cd ~/vote_app

# 3. Environment sozlash
nano api/.env  # yuqoridagi konfiguratsiyani kiriting
nano web/.env  # yuqoridagi konfiguratsiyani kiriting

# 4. Firewall sozlash
sudo ufw allow 22 && sudo ufw allow 2015 && sudo ufw allow 8000
sudo ufw enable

# 5. Ishga tushirish
docker-compose up -d --build

# 6. Database yaratish
docker exec -it voting_api python -m app.init_db

# 7. Tekshirish
curl http://localhost:8000/docs
curl http://localhost:2015
```

---

## Yordam

Agar qandaydir muammo bo'lsa:
- Loglarni tekshiring: `docker-compose logs -f`
- Container statusini tekshiring: `docker-compose ps`
- GitHub issues'ga murojaat qiling

Muvaffaqiyatli deploy! 🚀
