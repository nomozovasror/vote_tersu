# Troubleshooting Guide

Production'da login muammosi va boshqa keng tarqalgan muammolarni hal qilish.

## 🔐 Login Muammolari

### Symptom: "Login Failed" xatosi

#### Tezkor Hal Qilish:

```bash
# 1-usul: Fix script (eng oson)
./fix-login.sh
```

Bu script:
- ✅ Database'ni qayta yaratadi
- ✅ Yangi admin user yaratadi
- ✅ Container'larni restart qiladi

#### Manual Hal Qilish:

```bash
# 1. Container'lar ishlayotganini tekshirish
docker-compose ps

# 2. Database'ni reinitialize qilish
docker exec -it voting_api python -m app.init_db

# 3. Container'larni restart qilish
docker-compose restart

# 4. Default credentials bilan kirish
# Username: admin
# Password: admin123
```

#### Debug Qilish:

```bash
# Debug script ishga tushirish
./debug-login.sh

# Bu script tekshiradi:
# - Container ishlayotganini
# - Database mavjudligini
# - Admin user'lar borligini
# - Password verification
# - Environment variables
# - API accessibility
```

### Keng Tarqalgan Sabablar:

#### 1. Database Yo'q yoki Bo'sh

**Belgi:** "User not found" yoki "Table doesn't exist"

**Hal qilish:**
```bash
docker exec -it voting_api python -m app.init_db
docker-compose restart
```

#### 2. Noto'g'ri API URL

**Belgi:** Network error, CORS error

**Tekshirish:**
```bash
# web/.env faylini tekshiring
cat web/.env
# VITE_API_URL=http://your-server-ip:2013 bo'lishi kerak

# Agar noto'g'ri bo'lsa, to'g'rilang:
nano web/.env
# Keyin rebuild:
docker-compose down
docker-compose up -d --build
```

#### 3. CORS Muammosi

**Belgi:** Browser console'da "CORS policy" xatosi

**Hal qilish:**
```bash
# api/.env faylini tekshiring
nano api/.env
# FRONTEND_URL=http://your-server-ip:2013 bo'lishi kerak

# Restart qiling:
docker-compose restart api
```

#### 4. Firewall Portlarni Bloklagan

**Tekshirish:**
```bash
# Firewall statusini ko'rish
sudo ufw status

# Kerakli portlar ochiq bo'lishi kerak:
# 22/tcp    ALLOW       SSH
# 2014/tcp  ALLOW       API
# 2013/tcp  ALLOW       Frontend
```

**Hal qilish:**
```bash
sudo ufw allow 2013/tcp
sudo ufw allow 2014/tcp
sudo ufw reload
```

#### 5. Parol Hash Xato

**Belgi:** "Password incorrect" debug script'da

**Hal qilish:**
```bash
# Parolni reset qilish
./add-user.sh password

# Yoki yangi user yaratish
./add-user.sh add
```

### Browser Muammolari

#### Cache Muammosi

```bash
# 1. Browser cache'ni tozalash
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete

# 2. Incognito/Private window'da sinab ko'ring

# 3. Cookies'ni tozalash
# Browser DevTools (F12) -> Application -> Cookies
```

#### Network Xatolarini Tekshirish

```bash
# 1. Browser DevTools ochish (F12)
# 2. Network tab'ga o'tish
# 3. Login request'ni topish (POST /auth/login)
# 4. Response'ni ko'rish:
#    - 200: Success
#    - 401: Invalid credentials
#    - 404: API not found (URL xato)
#    - 500: Server error
#    - Failed: Network/CORS error
```

## 🗄️ Database Muammolari

### Database Corrupt Bo'lsa

```bash
# 1. Backup yaratish
cp data/voting.db data/voting_backup_$(date +%Y%m%d).db

# 2. Database'ni o'chirish
rm data/voting.db

# 3. Qayta yaratish
docker exec -it voting_api python -m app.init_db

# 4. Restart
docker-compose restart
```

### Database Lock Xatosi

```bash
# SQLite database locked xatosi
# Container'larni to'xtatish va qayta boshlash
docker-compose down
docker-compose up -d
```

## 🐳 Docker Muammolari

### Container Ishga Tushmaydi

```bash
# Loglarni ko'rish
docker-compose logs -f api
docker-compose logs -f web

# Container'larni rebuild qilish
docker-compose down
docker-compose up -d --build --force-recreate
```

### Port Already in Use

```bash
# Qaysi process portni ishlatayotganini topish
sudo lsof -i :2013
sudo lsof -i :2014

# Process'ni to'xtatish
sudo kill -9 <PID>

# Yoki boshqa portdan foydalanish
# docker-compose.yml'da portlarni o'zgartiring
```

### Disk Space Yo'q

```bash
# Docker'ni tozalash
docker system prune -a

# Unused images'ni o'chirish
docker image prune -a

# Unused volumes'ni o'chirish
docker volume prune
```

## 🌐 Network Muammolari

### API'ga Ulanish Mumkin Emas

```bash
# 1. API ishlayotganini tekshirish
curl http://localhost:2014/docs

# 2. Container IP'sini tekshirish
docker inspect voting_api | grep IPAddress

# 3. Container ichidan test
docker exec voting_api curl http://localhost:2014/docs
```

### WebSocket Ulanmaydi

```bash
# 1. Browser console'ni tekshirish (F12)
# "WebSocket connection failed" xatosini qidirish

# 2. WebSocket URL to'g'riligini tekshirish
# ws://your-server-ip:2014/ws/... bo'lishi kerak

# 3. Firewall WebSocket'ga ruxsat berishini tekshirish
sudo ufw status
```

## 📝 Logs va Monitoring

### Real-time Logs

```bash
# Barcha loglar
docker-compose logs -f

# Faqat API
docker-compose logs -f api

# Faqat Web
docker-compose logs -f web

# Oxirgi 100 ta log
docker-compose logs --tail=100
```

### Container Status

```bash
# Status ko'rish
docker-compose ps

# Resource usage
docker stats voting_api voting_web

# Container details
docker inspect voting_api
```

## 🔧 Configuration Muammolari

### Environment Variables Yuklanmagan

```bash
# 1. .env fayllar mavjudligini tekshirish
ls -la api/.env web/.env

# 2. Fayllarni o'qish
cat api/.env
cat web/.env

# 3. Container'da environment'ni tekshirish
docker exec voting_api env | grep -E "DATABASE|SECRET|FRONTEND"

# 4. Restart after changes
docker-compose down
docker-compose up -d
```

### SECRET_KEY Yo'q yoki Default

```bash
# api/.env faylini tekshiring
cat api/.env | grep SECRET_KEY

# Agar default bo'lsa, yangilab qo'ying:
nano api/.env
# SECRET_KEY=your-very-long-random-secret-key-minimum-32-characters

# Random key generatsiya qilish:
openssl rand -hex 32

# Restart:
docker-compose restart api
```

## 🚨 Emergency Commands

### Hamma Narsani Reset Qilish

```bash
# WARNING: Bu barcha ma'lumotlarni o'chiradi!

# 1. Container'larni to'xtatish
docker-compose down

# 2. Database'ni backup qilish
cp data/voting.db backups/emergency_backup_$(date +%Y%m%d_%H%M%S).db

# 3. Database'ni o'chirish
rm data/voting.db

# 4. Qayta boshlash
docker-compose up -d --build

# 5. Database'ni initialize qilish
docker exec -it voting_api python -m app.init_db
```

### Backup'dan Restore Qilish

```bash
# 1. Container'larni to'xtatish
docker-compose down

# 2. Hozirgi database'ni o'chirish
rm data/voting.db

# 3. Backup'ni restore qilish
cp backups/voting_backup_YYYYMMDD_HHMMSS.db data/voting.db

# 4. Qayta boshlash
docker-compose up -d
```

## 📞 Yordam

Agar yuqoridagi usullar ishlamasa:

1. **Debug script ishga tushiring:**
   ```bash
   ./debug-login.sh
   ```

2. **Fix script ishga tushiring:**
   ```bash
   ./fix-login.sh
   ```

3. **Loglarni tekshiring:**
   ```bash
   docker-compose logs -f api
   ```

4. **GitHub Issues'ga murojaat qiling:**
   - Loglar
   - Environment setup
   - Qaysi script ishlatganingiz
   - Qaysi xato paydo bo'lganini

## ✅ Healthcheck

Hamma narsa ishlayotganini tekshirish:

```bash
# 1. Container'lar
docker-compose ps
# STATUS: Up bo'lishi kerak

# 2. Portlar
netstat -tulpn | grep -E "2013|2014"
# 2013 va 2014 portlar LISTEN bo'lishi kerak

# 3. API
curl http://localhost:2014/docs
# HTML qaytishi kerak

# 4. Database
docker exec voting_api ls -lh /app/data/voting.db
# Fayl mavjud bo'lishi kerak

# 5. Admin user
./add-user.sh list
# Kamida 1 ta user ko'rinishi kerak
```

Barcha checklar o'tsa, sistem ishlaydi! ✅
