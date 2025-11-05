# ⚡ Tezkor Ishga Tushirish

## 🚀 Bir Buyruq bilan Ishga Tushirish

```bash
./START.sh
```

Bu script:
- ✅ Docker mavjud bo'lsa - Docker Compose'dan foydalanadi
- ✅ Docker bo'lmasa - Manual ravishda backend va frontend'ni ishga tushiradi

## 🌐 Kirish

Ishga tushgandan keyin:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Default Login:**
- Username: `admin`
- Password: `admin123`

## 🛑 To'xtatish

```bash
./STOP.sh
```

---

## 📋 Docker bilan (Tavsiya etiladi)

### 1. Docker Desktop'ni ishga tushiring

macOS uchun Docker Desktop dasturini oching.

### 2. Loyihani build qilish va ishga tushirish

```bash
# Build va ishga tushirish
docker-compose up --build

# Yoki background'da ishga tushirish
docker-compose up -d --build

# Log'larni ko'rish
docker-compose logs -f

# To'xtatish
docker-compose down
```

---

## 🔧 Manual Ishga Tushirish (Docker'siz)

### Backend

**Terminal 1:**

```bash
cd api

# Virtual environment yaratish (birinchi marta)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Dependencies o'rnatish
pip install -r requirements.txt

# Database yaratish
mkdir -p ../data
python -m app.init_db

# Server ishga tushirish
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

**Terminal 2:**

```bash
cd web

# Dependencies o'rnatish (birinchi marta)
npm install

# Environment setup
echo "VITE_API_URL=http://localhost:8000" > .env

# Dev server ishga tushirish
npm run dev
```

---

## ✅ Tekshirish

### Backend ishlayotganini tekshirish:

```bash
curl http://localhost:8000/health
# Natija: {"status":"healthy"}
```

### Frontend:

Brauzerni oching: http://localhost:5173

---

## 🎯 Birinchi Qadamlar

1. **Login**: http://localhost:5173/admin/login
   - Username: `admin`
   - Password: `admin123`

2. **Kandidatlarni Sync Qilish**:
   - Dashboard'da "Sync Candidates" tugmasini bosing

3. **Event Yaratish**:
   - "Create Event" tugmasini bosing
   - Event nomini va davomiyligini kiriting
   - Kandidatlarni tanlang

4. **Event'ni Boshlash**:
   - "Manage" → "Start Event"

5. **Linklar**:
   - "Copy Vote Link" - ovoz berish uchun
   - "Copy Display Link" - katta ekran uchun

---

## 🐛 Muammolarni Hal Qilish

### Port band?

```bash
# 8000 portni bo'shatish
lsof -ti:8000 | xargs kill -9

# 5173 portni bo'shatish
lsof -ti:5173 | xargs kill -9
```

### Database xatolari?

```bash
# Database'ni qayta yaratish
rm -rf data/voting.db
cd api
python -m app.init_db
```

### Docker ishlamayapti?

```bash
# Docker container'larni to'xtatish
docker-compose down

# Qayta build qilish
docker-compose build --no-cache

# Qayta ishga tushirish
docker-compose up -d
```

### Backend xatolari?

```bash
# Log'larni ko'rish
docker-compose logs api

# yoki manual:
cd api
source venv/bin/activate
uvicorn app.main:app --reload
```

---

## 📚 Qo'shimcha Ma'lumot

- [README.md](./README.md) - To'liq dokumentatsiya
- [SETUP.md](./SETUP.md) - Batafsil setup yo'riqnomasi
- [instructions.md](./instructions.md) - Loyiha talablari
