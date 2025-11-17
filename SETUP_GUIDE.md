# University Voting System - Setup Guide

Bu qo'llanma sizga ovoz berish tizimini o'z universitetingiz uchun sozlashda yordam beradi.

## Tez sozlash (Quick Setup)

### 1. .env fayllarni sozlash

#### Root `.env` fayli
```bash
cp .env.example .env
```

Quyidagi qiymatlarni o'zgartiring:

```env
# Universitet nomi
UNIVERSITY_NAME=Sizning universitetingiz nomi
UNIVERSITY_SHORT_NAME=UNIV

# Server IP yoki domain
SERVER_HOST=your-server-ip
API_PORT=2014
WEB_PORT=2013

# HEMIS API (O'zbekiston universitetlari uchun)
EXTERNAL_API_URL=https://student.your-university.uz/rest/v1/data/employee-list
EXTERNAL_API_TOKEN=your-hemis-api-token

# Xavfsizlik (ALBATTA O'ZGARTIRING!)
SECRET_KEY=your-very-long-random-secret-key-here
ADMIN_PASSWORD=your-strong-password

# URL'lar
FRONTEND_URL=http://your-server-ip:2013
BACKEND_URL=http://your-server-ip:2014
VITE_API_URL=http://your-server-ip:2014
```

#### API `.env` fayli
```bash
cp api/.env.example api/.env
```

Quyidagi qiymatlarni o'zgartiring:
```env
EXTERNAL_API_URL=https://student.your-university.uz/rest/v1/data/employee-list
EXTERNAL_API_TOKEN=your-hemis-api-token
SECRET_KEY=your-very-long-random-secret-key-here
ADMIN_PASSWORD=your-strong-password
BACKEND_URL=http://your-server-ip:2014
FRONTEND_URL=http://your-server-ip:2013
```

### 2. Docker bilan ishga tushirish

```bash
# Build va start
docker-compose -f docker-compose.prod.yml up --build -d

# Loglarni ko'rish
docker-compose -f docker-compose.prod.yml logs -f

# To'xtatish
docker-compose -f docker-compose.prod.yml down
```

### 3. Tizimga kirish

- **Frontend**: `http://your-server-ip:2013`
- **Admin panel**: `http://your-server-ip:2013/admin/login`
- **API docs**: `http://your-server-ip:2014/docs`

---

## O'zbekiston universitetlari uchun HEMIS sozlamalari

### HEMIS API URL formati

Har bir universitet o'zining HEMIS subdomain'iga ega:

| Universitet | HEMIS URL | API Endpoint |
|------------|-----------|--------------|
| TerDU | student.tersu.uz | https://student.tersu.uz/rest/v1/data/employee-list |
| TUIT | hemis.tuit.uz | https://hemis.tuit.uz/rest/v1/data/employee-list |
| TDIU | student.tsue.uz | https://student.tsue.uz/rest/v1/data/employee-list |
| NamMQI | student.nammqi.uz | https://student.nammqi.uz/rest/v1/data/employee-list |
| SamDU | student.samdu.uz | https://student.samdu.uz/rest/v1/data/employee-list |
| BuxDU | student.buxdu.uz | https://student.buxdu.uz/rest/v1/data/employee-list |

### API Token olish

1. HEMIS admin paneliga kiring
2. **Sozlamalar** → **API tokens** bo'limiga o'ting
3. Yangi token yarating
4. Tokenni `.env` fayliga qo'shing

---

## Portlarni o'zgartirish

Agar standart portlar (2013, 2014) band bo'lsa:

```env
# .env faylida
API_PORT=8001
WEB_PORT=8000

# URLlarni yangilang
FRONTEND_URL=http://your-server-ip:8000
BACKEND_URL=http://your-server-ip:8001
VITE_API_URL=http://your-server-ip:8001
```

Qayta build qiling:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up --build -d
```

---

## Xavfsizlik sozlamalari

### 1. SECRET_KEY generatsiya qilish

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Kuchli parol
- Minimum 12 belgidan iborat
- Katta va kichik harflar
- Raqamlar va maxsus belgilar

### 3. Firewall sozlamalari

```bash
# Ubuntu/Debian
sudo ufw allow 2013/tcp  # Web port
sudo ufw allow 2014/tcp  # API port

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=2013/tcp
sudo firewall-cmd --permanent --add-port=2014/tcp
sudo firewall-cmd --reload
```

---

## Performance sozlamalari

200+ foydalanuvchi uchun:

```env
# .env faylida
WEB_CONCURRENCY=6              # Worker soni (2 * CPU cores)
MAX_CONNECTIONS_PER_EVENT=500  # Har bir event uchun max ulanishlar
MAX_TOTAL_CONNECTIONS=2000     # Jami max ulanishlar
```

500+ foydalanuvchi uchun:
```env
WEB_CONCURRENCY=8
MAX_CONNECTIONS_PER_EVENT=1000
MAX_TOTAL_CONNECTIONS=5000
```

Docker resource limits'ni ham oshiring (`docker-compose.prod.yml`):
```yaml
deploy:
  resources:
    limits:
      cpus: '8'
      memory: 8G
```

---

## Monitoring

### WebSocket statistikasi
```bash
curl http://your-server-ip:2014/ws-stats
```

Response:
```json
{
  "total_vote_connections": 45,
  "total_display_connections": 2,
  "events_with_vote_connections": 1,
  "events_with_display_connections": 1
}
```

### Docker logs
```bash
# Barcha loglar
docker-compose -f docker-compose.prod.yml logs -f

# Faqat API
docker-compose -f docker-compose.prod.yml logs -f api

# Faqat Web
docker-compose -f docker-compose.prod.yml logs -f web
```

### Container stats
```bash
docker stats voting_api voting_web
```

---

## Muammolarni hal qilish

### WebSocket uzilishlari

1. Firewall'ni tekshiring
2. Reverse proxy timeout'larni oshiring (agar ishlatilsa)
3. Connection limits'ni tekshiring

### HEMIS API xatosi

1. Token'ni tekshiring
2. API endpoint URL'ni tekshiring
3. HEMIS tizimi ishlayotganini tekshiring

### Database xatosi

```bash
# Database'ni qayta yarating
docker-compose -f docker-compose.prod.yml down
rm -rf data/voting.db
docker-compose -f docker-compose.prod.yml up --build -d
```

---

## Yangilash

```bash
# Kodni yangilang
git pull

# Qayta build
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up --build -d
```

---

## Aloqa

Savollar yoki muammolar uchun GitHub issues oching.
