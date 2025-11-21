# Stress Testing Guide

Loyihani real foydalanuvchilarsiz test qilish uchun to'liq qo'llanma.

## 🚀 Tez Boshlash

### 1. Dependencies o'rnatish

```bash
# Python dependencies
pip install websockets aiohttp psutil

# Yoki virtual environment bilan
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install websockets aiohttp psutil
```

### 2. Serverni ishga tushirish

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Event yaratish

Admin panelga kiring va yangi event yaratib, link olish:

1. Browser: `http://localhost:2013/admin/login`
2. Login: `admin` / `admin123`
3. Dashboard → Create Event
4. Event yarating va **event link**'ni ko'chirib oling (UUID format)

---

## 📊 Quick Tests (Tayyor Skriptlar)

### Oddiy test (50 users)

```bash
./quick_test.sh <event-link> small
```

**Natija:** 50 ta concurrent user, 30 soniya

### O'rtacha test (100 users)

```bash
./quick_test.sh <event-link> medium
```

**Natija:** 100 ta concurrent user, 60 soniya

### Katta test (200 users)

```bash
./quick_test.sh <event-link> large
```

**Natija:** 200 ta concurrent user, 120 soniya

### Ekstremal test (500 users)

```bash
./quick_test.sh <event-link> extreme
```

**Ogohlantirish:** Bu test single worker setup bilan failga tushishi mumkin!

### Ramp-up test

```bash
./quick_test.sh <event-link> ramp
```

**Natija:** 60 soniya ichida 200 usergacha asta-sekin oshiradi, 120 soniya hold qiladi

### Voting test

```bash
./quick_test.sh <event-link> vote
```

**Natija:** 100 user + har biri ovoz beradi

---

## 🔧 Advanced Tests (Custom Parameters)

### Custom concurrent test

```bash
python3 stress_test.py \
    --api http://localhost:2014 \
    --link YOUR_EVENT_LINK \
    --users 150 \
    --duration 90 \
    --batch-size 50
```

**Parametrlar:**
- `--api` - API URL (default: http://localhost:2014)
- `--link` - Event link (UUID)
- `--users` - Concurrent users soni
- `--duration` - Test davomiyligi (soniyalarda)
- `--batch-size` - Bir vaqtda nechta user connect qilish

### Custom ramp-up test

```bash
python3 stress_test.py \
    --api http://localhost:2014 \
    --link YOUR_EVENT_LINK \
    --mode ramp \
    --max-users 250 \
    --ramp-time 120 \
    --hold-time 180
```

**Parametrlar:**
- `--mode ramp` - Ramp-up mode
- `--max-users` - Maksimal user soni
- `--ramp-time` - Qancha vaqtda maksimal usergacha yetish (s)
- `--hold-time` - Maksimal userlarda qancha turish (s)

### Voting bilan test

```bash
python3 stress_test.py \
    --api http://localhost:2014 \
    --link YOUR_EVENT_LINK \
    --users 100 \
    --duration 60 \
    --vote
```

**Izoh:** `--vote` flag user'lar ovoz berishini yoqadi (har user YES ovoz beradi)

---

## 📈 Test Natijalari Tushunish

### Sample Output

```
🚀 Starting Stress Test
  API URL:      http://localhost:2014
  Event Link:   abc-123-def-456
  Users:        200
  Duration:     120s
  Voting:       False
  Batch size:   50
======================================================================

📦 Batch 1/4: Connecting users 0-50...
✅ User   0 connected (0.145s)
✅ User   1 connected (0.152s)
...

📊 System Monitoring Started
Time                 Connections     CPU %      RAM MB     Files
----------------------------------------------------------------------
14:30:15            50              25.5       450.2      78
14:30:20            100             32.1       620.5      128
14:30:25            150             38.7       750.8      178
14:30:30            200             42.3       820.1      228

======================================================================
STRESS TEST NATIJALAR
======================================================================

📡 CONNECTION STATISTICS:
  Total attempts:      200
  ✅ Successful:        198 (99.00%)
  ❌ Failed:            2 (1.00%)

  Connection timing:
    Average: 0.156s
    Median:  0.148s
    Min:     0.125s
    Max:     0.245s

⚡ PERFORMANCE:
  Test duration:       122.45s
  Connections/sec:     1.63

======================================================================
✅ TEST PASSED - Success rate: 99.00%
======================================================================
```

### Metrikalar Tushuntirish

#### Connection Statistics
- **Total attempts** - Jami ulanish urinishlari
- **Successful** - Muvaffaqiyatli ulanishlar
- **Failed** - Xatolik bilan tugagan ulanishlar
- **Connection timing** - Ulanish tezligi statistikasi

#### Vote Statistics (agar `--vote` ishlatilsa)
- **Total votes** - Jami ovozlar
- **Successful** - Muvaffaqiyatli ovozlar
- **Vote timing** - Ovoz berish tezligi
- **Votes/sec** - Soniyasiga ovozlar soni

#### Performance
- **Test duration** - Test davomiyligi
- **Connections/sec** - Soniyasiga ulanishlar

#### System Monitoring
- **Connections** - Aktiv WebSocket connections
- **CPU %** - CPU foydalanish foizi
- **RAM MB** - RAM ishlatilishi (MB)
- **Files** - Ochiq file descriptors soni

---

## ✅ Success Criteria

### Test muvaffaqiyatli (PASSED)
- Success rate ≥ 95%
- Connection time < 1s (average)
- Vote time < 500ms (agar vote enabled)

### Test ogohlantirish (WARNING)
- Success rate 80-95%
- Connection time 1-2s
- Ba'zi errors mavjud

### Test failed
- Success rate < 80%
- Ko'p xatoliklar
- System overload

---

## 🐛 Troubleshooting

### Test yuklana olmayapti

```bash
# Check dependencies
pip list | grep -E "websockets|aiohttp"

# Reinstall if needed
pip install --upgrade websockets aiohttp psutil
```

### "Connection refused" xatosi

```bash
# Check if server is running
curl http://localhost:2014/health

# Check Docker containers
docker ps | grep voting

# Restart if needed
docker-compose restart
```

### "Event not found" xatosi

1. Event link to'g'riligini tekshiring
2. Admin panelda event "active" holatda ekanligini tekshiring
3. Timer boshlangan bo'lishi kerak (voting uchun)

### 30-50 userdan keyin failed

Bu **file descriptor limit** muammosi. Tuzatish:

```bash
# Check ulimits
docker exec voting_api sh -c "ulimit -n"
# Should be: 65536

# If 1024, fix docker-compose.yml
docker-compose down
docker-compose up -d --force-recreate

# Verify
docker exec voting_api sh -c "ulimit -n"
```

### High CPU yoki Memory

```bash
# Monitor real-time
docker stats voting_api

# Check logs
docker logs voting_api --tail 100

# Get system stats
curl http://localhost:2014/ws-stats
```

---

## 📊 Test Scenarios

### Scenario 1: Baseline Test (Bazaviy test)

**Maqsad:** Sistemaning asosiy imkoniyatini aniqlash

```bash
./quick_test.sh <event-link> small
./quick_test.sh <event-link> medium
./quick_test.sh <event-link> large
```

**Kutilgan natija:** 200 users - 95%+ success rate

### Scenario 2: Peak Load Test (Eng yuqori yuk)

**Maqsad:** Sistem qachon ishdan chiqishini topish

```bash
# Start with known working capacity
./quick_test.sh <event-link> large

# Push further
python3 stress_test.py --api http://localhost:2014 --link <event-link> --users 250 --duration 60

# Even further
python3 stress_test.py --api http://localhost:2014 --link <event-link> --users 300 --duration 60
```

**Monitoring:**
```bash
# Terminal 1: Run test
# Terminal 2: Monitor
watch -n 1 'curl -s http://localhost:2014/ws-stats | jq'
```

### Scenario 3: Endurance Test (Chidamlilik)

**Maqsad:** Uzoq vaqt ishlashni test qilish

```bash
python3 stress_test.py \
    --api http://localhost:2014 \
    --link <event-link> \
    --users 100 \
    --duration 600  # 10 minutes
```

### Scenario 4: Real-world Simulation

**Maqsad:** Real voting jarayonini simulyatsiya qilish

```bash
# Step 1: Ramp up (users entering voting page)
python3 stress_test.py \
    --api http://localhost:2014 \
    --link <event-link> \
    --mode ramp \
    --max-users 150 \
    --ramp-time 120 \
    --hold-time 300

# Step 2: Voting phase (Admin panelda timer start qiling!)
python3 stress_test.py \
    --api http://localhost:2014 \
    --link <event-link> \
    --users 150 \
    --duration 180 \
    --vote
```

### Scenario 5: Spike Test (To'satdan ko'tarilish)

**Maqsad:** To'satdan ko'p user kelishi

```bash
# Rapid connections
python3 stress_test.py \
    --api http://localhost:2014 \
    --link <event-link> \
    --users 200 \
    --duration 30 \
    --batch-size 100  # Large batches = faster spike
```

---

## 📝 Best Practices

### 1. Ketma-ket test qilish

```bash
# Small → Medium → Large
./quick_test.sh <link> small
sleep 10
./quick_test.sh <link> medium
sleep 10
./quick_test.sh <link> large
```

### 2. Monitoring bilan test qilish

```bash
# Terminal 1: Monitoring
watch -n 1 'curl -s http://localhost:2014/ws-stats | jq'

# Terminal 2: Test
./quick_test.sh <link> large
```

### 3. Loglarni saqlash

```bash
# Save test results
./quick_test.sh <link> large 2>&1 | tee test_results_$(date +%Y%m%d_%H%M%S).log

# Save system stats
curl http://localhost:2014/ws-stats > stats_before.json
./quick_test.sh <link> large
curl http://localhost:2014/ws-stats > stats_after.json
```

### 4. Database backup (uzun testlar uchun)

```bash
# Backup before test
cp data/voting.db data/voting.db.backup

# After test, restore if needed
cp data/voting.db.backup data/voting.db
docker-compose restart
```

---

## 🎯 Target Benchmarks

### Minimal (Small university, 50-100 users)
- 100 concurrent users
- 95%+ success rate
- < 1s connection time
- < 500ms vote time

### Standard (Medium university, 100-200 users)
- 200 concurrent users
- 95%+ success rate
- < 1s connection time
- < 500ms vote time

### Large (Big university, 300-500 users)
- 500 concurrent users
- 90%+ success rate
- < 2s connection time
- < 1s vote time

**Izoh:** Large test uchun Redis pub/sub kerak bo'ladi (hozirda single worker bilan 200-250 limit).

---

## 🔗 Qo'shimcha Resurslar

- **PERFORMANCE.md** - To'liq performance guide, Redis setup
- **SETUP_GUIDE.md** - Production deployment
- `/ws-stats` endpoint - Real-time monitoring

---

## ❓ FAQ

**Q: Nechta user bilan test qilishim kerak?**
A: Real foydalanuvchilar sonidan 1.5-2x ko'p test qiling. Agar 150 user kutilsa, 200-300 bilan test qiling.

**Q: Test davomida real users bor bo'lsa-chi?**
A: Test uchun alohida event yarating. Real eventni test qilmang!

**Q: Qaysi test type eng yaxshi?**
A: Ketma-ket: small → medium → large → ramp (gradual)

**Q: Test failed, nima qilaman?**
A: Troubleshooting bo'limiga qarang yoki PERFORMANCE.md'da Redis setup qiling.

**Q: Production serverda test qilsam bo'ladimi?**
A: Yo'q! Faqat development yoki staging serverda test qiling. Production'da load test xavfli!

---

## 📞 Help

Muammolar yoki savollar uchun:
1. PERFORMANCE.md faylini o'qing
2. GitHub issues oching
3. Logs tekshiring: `docker logs voting_api`
