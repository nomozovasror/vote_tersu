# Rebuild Guide - psutil Fix

## Muammo

`psutil` package build qilish uchun `gcc` compiler kerak edi. Dockerfile'da system dependencies qo'shildi.

## Yechim

Dockerfile yangilandi va quyidagi paketlar qo'shildi:
- `gcc` - C compiler
- `python3-dev` - Python development headers

## 🔧 Rebuild Qilish

### Development (docker-compose.yml)

```bash
# Stop containers
docker-compose down

# Remove old images (optional, but recommended)
docker image rm voting_api voting_web

# Rebuild with no cache
docker-compose build --no-cache

# Start
docker-compose up -d

# Check logs
docker-compose logs -f api
```

### Production (docker-compose.prod.yml)

```bash
# Stop containers
docker-compose -f docker-compose.prod.yml down

# Remove old images (optional)
docker image rm voting_api voting_web

# Rebuild
docker-compose -f docker-compose.prod.yml build --no-cache

# Start
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f api
```

## ✅ Tekshirish

```bash
# 1. Check if containers are running
docker ps | grep voting

# 2. Check API health
curl http://localhost:2014/health

# 3. Test monitoring endpoint (uses psutil)
curl http://localhost:2014/ws-stats

# Expected response with system stats:
{
  "total_vote_connections": 0,
  "total_display_connections": 0,
  "events_with_vote_connections": 0,
  "events_with_display_connections": 0,
  "system": {
    "cpu_percent": 2.5,
    "memory_mb": 120.5,
    "open_files": 15,
    "threads": 3,
    "connections": 5
  }
}
```

## 🐛 Agar Muammo Davom Etsa

### Docker cache muammosi

```bash
# Complete cleanup
docker-compose down -v
docker system prune -a --volumes
docker-compose build --no-cache
docker-compose up -d
```

### Platform-specific build

Agar ARM64 (M1/M2 Mac) yoki boshqa architecture'da muammo bo'lsa:

```bash
# Force platform
docker-compose build --no-cache --build-arg BUILDPLATFORM=linux/amd64

# Or in Dockerfile, add:
# FROM --platform=linux/amd64 python:3.11-slim
```

### Alternative: Pre-built psutil

Agar gcc bilan muammo davom etsa, requirements.txt'da psutil versiyasini o'zgartiring:

```txt
# Use binary wheel (faster, no compilation needed)
psutil==5.9.8  # has more pre-built wheels
```

### Monitor without psutil

Agar psutil muammo qilsa, monitoring'ni psutil'siz ham ishlash mumkin:

**api/app/main.py'da:**

```python
@app.get("/ws-stats")
def websocket_stats():
    """Get WebSocket connection statistics for monitoring."""
    from .services.websocket_manager import manager

    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())

        stats = manager.get_connection_stats()
        stats["system"] = {
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "open_files": len(process.open_files()),
            "threads": process.num_threads(),
            "connections": len(process.connections()),
        }
    except ImportError:
        # psutil not available, return basic stats only
        stats = manager.get_connection_stats()
        stats["system"] = {"status": "psutil not available"}

    return stats
```

## 📝 O'zgarishlar

| Fayl | O'zgarish |
|------|-----------|
| `api/Dockerfile` | gcc va python3-dev qo'shildi |
| `api/requirements.txt` | psutil 5.9.6 (unchanged) |

## 🚀 Keyingi Qadamlar

Build muvaffaqiyatli bo'lgandan keyin:

1. ✅ Health check
2. ✅ Monitoring endpoint test
3. ✅ Stress test
   ```bash
   pip install -r stress_test_requirements.txt
   ./quick_test.sh <event-link> small
   ```
4. ✅ Full monitoring test
   ```bash
   python3 monitor.py --api http://localhost:2014
   ```

## 💡 Pro Tips

1. **Always use --no-cache for major changes**
   ```bash
   docker-compose build --no-cache
   ```

2. **Check build logs for errors**
   ```bash
   docker-compose build --progress=plain 2>&1 | tee build.log
   ```

3. **Monitor build time**
   - First build: ~2-3 minutes (downloads & compiles)
   - Subsequent builds: ~30s-1min (with cache)

4. **Image size**
   ```bash
   docker images | grep voting
   # Should be ~500-600MB for api
   ```

## ❓ FAQ

**Q: Build hali ham fail bo'lyapti?**
A: Docker logs'ni to'liq ko'ring:
```bash
docker-compose build --no-cache --progress=plain
```

**Q: psutil kerakmi?**
A: Monitoring uchun foydali, lekin majburiy emas. Basic stats psutil'siz ham ishlaydi.

**Q: Build juda sekin?**
A: Normal. psutil compile qilish 10-30 soniya oladi. Faqat birinchi marta.

**Q: Production'da ham rebuild kerakmi?**
A: Ha, lekin oldin development'da test qiling!

---

**Build muvaffaqiyatli bo'lganidan keyin stress test qilishingiz mumkin!** 🚀
