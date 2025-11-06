# Multi-Device Voting Fix

## 🎯 Muammo

Bir WiFi'dan bir nechta qurilma orqali ovoz berishda muammo:
- ❌ Barcha qurilmalar bir xil IP address'ga ega
- ❌ IP orqali duplicate tekshirish bilan faqat bitta qurilmadan ovoz berish mumkin
- ❌ "Siz allaqachon ovoz bergansiz" xatosi

## ✅ Yechim: Device Fingerprinting

Har bir qurilmaga unique ID beriladi:
- **IP Address** - WiFi/network identifikatsiyasi
- **Device ID** - Browser fingerprint (qurilma identifikatsiyasi)

### Device ID Tarkibi:

```javascript
{
  userAgent: "Mozilla/5.0 ...",
  language: "uz",
  platform: "MacIntel",
  screenResolution: "1920x1080x24",
  timezone: -300,
  colorDepth: 24,
  hardwareConcurrency: 8,
  deviceMemory: 8,
  touchSupport: false
}
```

Hash + timestamp + random → Unique Device ID

**Misol:** `lq2k9j8-8a7d3f2b-9x4m2p1k`

---

## 🔧 Texnik O'zgarishlar

### 1. Frontend (`web/src/`)

**Yangi fayllar:**
- ✅ `utils/deviceId.ts` - Device fingerprint generator

**O'zgargan fayllar:**
- ✅ `pages/VotePage.tsx` - Device ID yuborish

**Kod:**
```typescript
import { getDeviceId } from '../utils/deviceId';

const deviceId = useRef(getDeviceId());

// Vote yuborishda:
wsRef.current.send(JSON.stringify({
  type: 'cast_vote',
  vote_type: voteType,
  candidate_id: candidateId,
  nonce: nonce.current,
  device_id: deviceId.current  // ← YANGI
}));
```

### 2. Backend (`api/app/`)

**Model o'zgarishi:**
- ✅ `models/vote.py` - `device_id` column qo'shildi

**Database migration:**
- ✅ `core/database.py` - `ALTER TABLE votes ADD COLUMN device_id`

**WebSocket handler:**
- ✅ `routes/websocket.py` - Device ID + IP orqali tekshirish

**Kod:**
```python
device_id = data.get("device_id")

# Duplicate check with device_id
if device_id:
    existing_vote = db.query(Vote).filter(
        Vote.event_id == event.id,
        Vote.candidate_id == candidate_id,
        Vote.ip_address == client_ip,
        Vote.device_id == device_id  # ← YANGI
    ).first()
```

---

## 📊 Voting Logikasi

### Eski (IP only):

```
User A (Phone)  ─┐
User B (Laptop) ─┼─→ WiFi Router → IP: 192.168.1.100
User C (Tablet) ─┘

✅ User A votes → OK
❌ User B votes → "Already voted" (same IP)
❌ User C votes → "Already voted" (same IP)
```

### Yangi (IP + Device ID):

```
User A (Phone)  → IP: 192.168.1.100 + Device: aaa111
User B (Laptop) → IP: 192.168.1.100 + Device: bbb222
User C (Tablet) → IP: 192.168.1.100 + Device: ccc333

✅ User A votes → OK (192.168.1.100 + aaa111)
✅ User B votes → OK (192.168.1.100 + bbb222)
✅ User C votes → OK (192.168.1.100 + ccc333)
```

---

## 🗄️ Database Schema

**votes table:**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| event_id | INTEGER | Event FK |
| candidate_id | INTEGER | Candidate FK |
| ip_address | VARCHAR | IP manzil |
| **device_id** | **VARCHAR** | **Device fingerprint (YANGI)** |
| nonce | VARCHAR | Vote nonce |
| vote_type | VARCHAR | yes/no/neutral |
| timestamp | DATETIME | Vote vaqti |

**Unique constraint:** `(event_id, candidate_id, ip_address, device_id)`

---

## 🚀 Deployment

### 1. Backend Restart

Database migration avtomatik ishga tushadi:

```bash
cd /Users/asrornomozov/Desktop/vote_app

# Docker
docker-compose down
docker-compose up -d --build

# Yoki manual
cd api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 2013
```

Backend ishga tushganda:
```
[INFO] Applying schema migration: device_id column added to votes
```

### 2. Frontend Rebuild (allaqachon qilingan)

```bash
cd web
npm run build
```

Build: `dist/assets/index-BxvR3z-R.js`

### 3. Docker Restart

```bash
docker-compose up -d --build
```

---

## 🧪 Testing

### Scenario 1: Bitta WiFi, 3 ta qurilma

1. **Phone'dan vote:**
   ```
   IP: 192.168.1.100
   Device ID: abc-123-xyz
   Result: ✅ Vote accepted
   ```

2. **Laptop'dan vote:**
   ```
   IP: 192.168.1.100 (same)
   Device ID: def-456-uvw (different)
   Result: ✅ Vote accepted
   ```

3. **Tablet'dan vote:**
   ```
   IP: 192.168.1.100 (same)
   Device ID: ghi-789-rst (different)
   Result: ✅ Vote accepted
   ```

### Scenario 2: Bir qurilmadan ikkinchi marta

1. **Phone'dan birinchi vote:**
   ```
   IP: 192.168.1.100
   Device ID: abc-123-xyz
   Result: ✅ Vote accepted
   ```

2. **Phone'dan ikkinchi vote:**
   ```
   IP: 192.168.1.100 (same)
   Device ID: abc-123-xyz (same)
   Result: ❌ "Siz allaqachon ovoz bergansiz (bu qurilmadan)"
   ```

---

## 🔍 Debug

### Browser Console:

```javascript
// Device ID tekshirish
localStorage.getItem('voting_device_id')
// "lq2k9j8-8a7d3f2b-9x4m2p1k"

// Device info
console.log('[DeviceID] Fingerprint:', {
  userAgent: navigator.userAgent,
  platform: navigator.platform,
  screen: screen.width + 'x' + screen.height
})
```

### Backend Logs:

```bash
docker-compose logs api | grep device_id
```

### Database Query:

```sql
-- Bir IP'dan nechta turli qurilma vote berdi?
SELECT
  ip_address,
  COUNT(DISTINCT device_id) as device_count,
  COUNT(*) as total_votes
FROM votes
WHERE event_id = 1
GROUP BY ip_address
HAVING device_count > 1;
```

---

## 🛡️ Privacy & Security

### Device ID:
- ✅ Browser localStorage'da saqlanadi
- ✅ Faqat voting uchun ishlatiladi
- ✅ User personal data emas
- ✅ Server'da faqat hash ko'rinishida
- ✅ Cross-site tracking yo'q

### Fraud Prevention:
- ✅ IP + Device ID kombinatsiyasi
- ✅ Nonce (one-time use)
- ✅ Timer validation
- ✅ Event status check

---

## 🔄 Backward Compatibility

Eski vote'lar (`device_id = NULL`):
- ✅ Eski vote'lar saqlanadi
- ✅ IP-only check fallback
- ✅ Migration o'chirmasdan qo'shadi

---

## 📝 Summary

| Feature | Status | Tavsif |
|---------|--------|---------|
| Device fingerprinting | ✅ | Browser-based unique ID |
| Multi-device voting | ✅ | Bir WiFi'dan ko'p qurilma |
| Database migration | ✅ | Avtomatik `device_id` column |
| Frontend integration | ✅ | Device ID yuborish |
| Backend validation | ✅ | IP + Device ID check |
| Backward compatible | ✅ | Eski vote'lar ishlaydi |

---

## ✅ DEPLOY QILINGAN!

```bash
cd /Users/asrornomozov/Desktop/vote_app
docker-compose up -d --build
```

**Test qiling:**
1. Telefon va laptop'dan bir xil WiFi orqali vote bering
2. Ikkala vote ham qabul qilinishi kerak
3. Browser console'da device ID ko'rish mumkin

🎉 **Muammo hal qilindi!**
