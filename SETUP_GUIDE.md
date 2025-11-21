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

⚠️ **MUHIM: WebSocket Worker sozlamalari**

Tizim in-memory WebSocket broadcast ishlatadi va **bitta worker talab qiladi**:

```env
# .env faylida - MAJBURIY!
WEB_CONCURRENCY=1              # WebSocket uchun FAQAT 1 worker
MAX_CONNECTIONS_PER_EVENT=500  # Har bir event uchun max ulanishlar
MAX_TOTAL_CONNECTIONS=2000     # Bitta worker 2000 ta ulanish
```

**Nima uchun bitta worker?**

Multi-worker rejimida har bir worker o'z `ConnectionManager` instance'iga ega. Agar timer start worker #1 da bajarilsa, faqat worker #1 dagi ulanishlar yangilanadi. Worker #2, #3 da ulanganlar yangilanish olmaydi.

**Alternativ yechim (kelajakda):**

500+ foydalanuvchi yoki multi-worker kerak bo'lsa:
- Redis pub/sub ishlatish
- PostgreSQL LISTEN/NOTIFY ishlatish
- Sticky sessions sozlash

**Hozirgi imkoniyatlar:**

**Optimizatsiyalar:**
- ✅ SQLite WAL mode (concurrent reads/writes)
- ✅ Connection pooling (60 connections)
- ✅ Database indexes (fast queries)
- ✅ Async broadcast (parallel messaging)

**Imkoniyatlar:**
- ✅ 200 foydalanuvchi - Barqaror
- ✅ 1200+ votes/min - Ishlaydi
- ✅ 5-10ms latency - Yaxshi

**Batafsil:** [PERFORMANCE.md](PERFORMANCE.md) ga qarang

Docker resource limits (`docker-compose.prod.yml`):
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

---

## Monitoring

### WebSocket statistikasi (Kengaytirilgan)
```bash
curl http://your-server-ip:2014/ws-stats
```

Response (yangi optimizatsiyalar bilan):
```json
{
  "total_vote_connections": 200,
  "total_display_connections": 5,
  "events_with_vote_connections": 1,
  "events_with_display_connections": 1,
  "system": {
    "cpu_percent": 30.5,
    "memory_mb": 800.0,
    "open_files": 220,
    "threads": 10,
    "connections": 205
  }
}
```

**Yangi system metrics:**
- `cpu_percent` - CPU ishlatilishi (%)
- `memory_mb` - RAM ishlatilishi (MB)
- `open_files` - Ochiq file descriptor'lar soni
- `threads` - Thread'lar soni
- `connections` - Jami network connections

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

### Timer start yoki candidate o'zgarishi yangilanmayapti

**Sabab:** Multi-worker rejimida ishlayapti

**Hal qilish:**
```bash
# .env faylini tekshiring
cat .env | grep WEB_CONCURRENCY

# Agar 1 dan katta bo'lsa:
# .env ni tahrirlang
WEB_CONCURRENCY=1

# Qayta ishga tushiring
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up --build -d
```

### WebSocket uzilishlari

1. Firewall'ni tekshiring
2. Reverse proxy timeout'larni oshiring (agar ishlatilsa)
3. Connection limits'ni tekshiring
4. Browser console'da WebSocket xatolarini tekshiring

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

## Performance va Scalability

### Hozirgi imkoniyat (bitta worker)

**Optimizatsiyalar:**
- ✅ Docker ulimits (65536 file descriptors)
- ✅ Uvloop event loop (2-4x tezroq)
- ✅ Database session management tuzatildi
- ✅ Increased concurrency limits (5000)
- ✅ Performance monitoring endpoint

**Imkoniyat:**
- 200-250 concurrent users ✅
- 1000+ votes/minute
- 5-10ms latency
- ~800MB RAM usage

### WebSocket connection muammosi (30 user limit)

Agar tizim 30 ta foydalanuvchidan keyin yangi connection'larni rad etsa:

```bash
# 1. Ulimits tekshirish
docker exec ${CONTAINER_PREFIX}_api sh -c "ulimit -n"
# Kutilgan: 65536
# Agar 1024 bo'lsa, docker-compose.prod.yml'da ulimits mavjudligini tekshiring

# 2. Container'larni force recreate qiling
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --force-recreate

# 3. Docker daemon restart (agar kerak bo'lsa)
sudo systemctl restart docker
docker-compose -f docker-compose.prod.yml up -d
```

### Load Testing

```bash
# Test script yaratish
cat > test_load.py << 'EOF'
import asyncio
import websockets
import json
import sys

async def connect_user(link, user_id):
    uri = f"ws://localhost:2014/ws/vote/{link}"
    try:
        async with websockets.connect(uri) as ws:
            print(f"✅ User {user_id} connected")
            response = await ws.recv()
            await asyncio.sleep(60)
            return True
    except Exception as e:
        print(f"❌ User {user_id} error: {e}")
        return False

async def test_concurrent_users(link, num_users):
    print(f"\n🚀 Testing {num_users} concurrent users...")
    tasks = [connect_user(link, i) for i in range(num_users)]
    results = await asyncio.gather(*tasks)
    successful = sum(1 for r in results if r)
    print(f"\n📊 Results: {successful}/{num_users} successful")
    return successful

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_load.py <event_link> <num_users>")
        sys.exit(1)
    link = sys.argv[1]
    num_users = int(sys.argv[2])
    asyncio.run(test_concurrent_users(link, num_users))
EOF

# Test run
pip install websockets
python test_load.py "your-event-link" 200
```

### Agar 500+ foydalanuvchi kerak bo'lsa

`PERFORMANCE.md` faylida Redis pub/sub va PostgreSQL migration haqida to'liq guide mavjud.

---

## Yangilash (Yangi optimizatsiyalar bilan)

### Oddiy yangilash

```bash
# 1. Kodni yangilang
git pull

# 2. Qayta build qiling (no-cache bilan to'liq rebuild)
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 3. Monitoring
docker-compose -f docker-compose.prod.yml logs -f api

# 4. WebSocket connections tekshirish
curl http://your-server-ip:2014/ws-stats
```

### Performance optimizatsiyalaridan keyin (MUHIM!)

Agar siz ushbu commit'dan keyin yangilayotgan bo'lsangiz (30 user limit fix):

```bash
# 1. Stop containers
docker-compose -f docker-compose.prod.yml down

# 2. Update code
git pull

# 3. Update environment variables
cat >> .env << 'EOF'
MAX_CONNECTIONS_PER_EVENT=1000
MAX_TOTAL_CONNECTIONS=5000
EOF

# 4. Rebuild with new optimizations
docker-compose -f docker-compose.prod.yml build --no-cache

# 5. Start with force recreate
docker-compose -f docker-compose.prod.yml up -d --force-recreate

# 6. Verify ulimits
docker exec ${CONTAINER_PREFIX}_api sh -c "ulimit -n"
# Expected: 65536

# 7. Test with monitoring
curl http://your-server-ip:2014/ws-stats
```

### Rollback (agar muammo bo'lsa)

```bash
# Previous commit'ga qaytish
git log --oneline  # commit hash'ni topish
git checkout <previous-commit-hash>

# Rebuild
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up --build -d
```

---

## Aloqa

Savollar yoki muammolar uchun GitHub issues oching.
