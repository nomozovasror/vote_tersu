# 🚀 Loyihani Ishga Tushirish Yo'riqnomasi

## Tezkor Ishga Tushirish (Docker bilan)

### 1. Loyiha fayllarini tayyorlash

Barcha kerakli fayllar allaqachon yaratilgan. Faqat `.env` faylni tekshiring:

```bash
# .env fayli loyiha ildizida mavjud, kerak bo'lsa o'zgartiring
cat .env
```

### 2. Docker bilan ishga tushirish

```bash
# Docker containerlarni build qilish va ishga tushirish
docker-compose up --build
```

Buning natijasida:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

### 3. Dastlabki kirish

- **URL**: http://localhost:5173/admin/login
- **Username**: admin
- **Password**: admin123

---

## Manual Ishga Tushirish (Docker'siz)

### Backend Setup

1. **Virtual environment yaratish**:
```bash
cd api
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# yoki Windows uchun: venv\Scripts\activate
```

2. **Dependencies o'rnatish**:
```bash
pip install -r requirements.txt
```

3. **Database yaratish**:
```bash
# data papkasini yaratish
mkdir -p ../data

# Database'ni initialize qilish
python -m app.init_db
```

4. **Backend serverini ishga tushirish**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

Yangi terminal oynasida:

1. **Dependencies o'rnatish**:
```bash
cd web
npm install
```

2. **Environment o'rnatish**:
```bash
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. **Dev server ishga tushirish**:
```bash
npm run dev
```

---

## ✅ Tekshirish

### Backend tekshirish:
```bash
curl http://localhost:8000/health
# Javob: {"status":"healthy"}
```

### API Documentation:
Brauzerda: http://localhost:8000/docs

### Frontend tekshirish:
Brauzerda: http://localhost:5173

---

## 📝 Birinchi Qadamlar

1. **Admin panelga kirish**: http://localhost:5173/admin/login
   - Username: `admin`
   - Password: `admin123`

2. **Kandidatlarni sync qilish**:
   - Dashboard'da "Sync Candidates" tugmasini bosing
   - Bu tashqi API'dan kandidatlarni yuklab oladi

3. **Voqelik (Event) yaratish**:
   - "Create Event" tugmasini bosing
   - Event nomini kiriting
   - Ovoz berish davomiyligini kiriting (default: 15 soniya)
   - Kandidatlarni tanlang
   - "Create Event" tugmasini bosing

4. **Event'ni boshlash**:
   - "Manage" tugmasini bosing
   - "Start Event" tugmasini bosing

5. **Ovoz berish linkini olish**:
   - "Copy Vote Link" tugmasini bosing
   - Bu linkni ovoz beruvchilarga ulashing

6. **Display screen'ni boshqarish**:
   - Kandidatni tanlang
   - Countdown vaqtini kiriting
   - "Update Display" tugmasini bosing
   - "Copy Display Link" tugmasi bilan display linkini oling

---

## 🎯 Asosiy URL'lar

| Maqsad | URL |
|--------|-----|
| Admin Login | http://localhost:5173/admin/login |
| Admin Dashboard | http://localhost:5173/admin/dashboard |
| Ovoz berish | http://localhost:5173/vote/[event-link] |
| Display Screen | http://localhost:5173/display/[event-link] |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## 🔧 Muammolarni Hal Qilish

### Backend ishlamayapti?
```bash
# Log'larni tekshiring
docker-compose logs api

# yoki manual setup uchun:
cd api
source venv/bin/activate
python -m app.init_db
uvicorn app.main:app --reload
```

### Frontend ishlamayapti?
```bash
# Log'larni tekshiring
docker-compose logs web

# yoki manual setup uchun:
cd web
npm install
npm run dev
```

### Database xatolari?
```bash
# Database'ni qayta yaratish
rm -rf data/voting.db
cd api
python -m app.init_db
```

### WebSocket ulanmayapti?
- Backend ishlayotganini tekshiring: http://localhost:8000/health
- CORS sozlamalarini tekshiring
- Browser console'da xatolarni tekshiring

---

## 📦 Production Deploy

### Docker bilan:
```bash
# Production build
docker-compose -f docker-compose.yml up -d

# Log'larni ko'rish
docker-compose logs -f
```

### Muhim eslatmalar:
1. `.env` faylidagi `SECRET_KEY`'ni o'zgartiring
2. `ADMIN_PASSWORD`'ni o'zgartiring
3. Production database (PostgreSQL) ishlatishni o'ylab ko'ring
4. HTTPS sozlang
5. Firewall sozlamalarini tekshiring

---

## 🎓 Qo'shimcha Ma'lumot

Batafsil ma'lumot uchun:
- [README.md](./README.md) - To'liq dokumentatsiya
- [instructions.md](./instructions.md) - Asl talablar
- API Docs: http://localhost:8000/docs

---

## 🆘 Yordam

Muammo yuzaga kelsa:
1. Barcha servislar ishga tushganini tekshiring
2. Log'larni o'qing
3. Browser console'ni tekshiring
4. .env faylini tekshiring
5. Port'lar band emasligini tekshiring (8000, 5173)
