# Port Konfiguratsiyasi

## Frontend Port: 2015

Frontend 2015 portda ochiladi. Buni sozlash uchun:

### 1. Docker Compose (docker-compose.yml)
```yaml
web:
  ports:
    - "2015:80"  # Host:Container
```
- **2015**: Server/kompyuterda ochiq port (global)
- **80**: Container ichidagi Nginx port (internal)

### 2. Web/.env Fayli
```env
VITE_API_URL=http://localhost:8000
```
**Muhim**: Web/.env faylida frontend portini ko'rsatish SHART EMAS!
- Bu fayl faqat **API URL**ni saqlaydi
- Frontend'ning o'zi qaysi portda ochilishi Docker Compose'da belgilanadi

## API Port: 8000

Backend 8000 portda ochiladi:

### Docker Compose
```yaml
api:
  ports:
    - "8000:8000"
```

### API/.env Fayli
```env
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:2015
```

## Port Mapping Tushuntirilishi

### Development (Local)
```
Browser → http://localhost:2015 → Docker Container (Nginx:80) → React App
Browser → http://localhost:8000 → Docker Container (FastAPI:8000) → Backend
```

### Production (Server)
```
Browser → http://server-ip:2015 → Docker Container (Nginx:80) → React App
Browser → http://server-ip:8000 → Docker Container (FastAPI:8000) → Backend
```

## URL'lar

### Local Development
- Frontend: `http://localhost:2015`
- API: `http://localhost:8000`
- Admin Panel: `http://localhost:2015/admin/login`

### Production
- Frontend: `http://your-server-ip:2015`
- API: `http://your-server-ip:8000`
- Admin Panel: `http://your-server-ip:2015/admin/login`

## Firewall (Production)

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 2015/tcp    # Frontend (global port)
sudo ufw allow 8000/tcp    # API (global port)
```

## Tez-tez so'raladigan savollar

### Q: Web/.env da frontend portini ko'rsatish kerakmi?
**A**: Yo'q! Web/.env faqat backend API URL'ni saqlaydi. Frontend portini Docker Compose sozlaydi.

### Q: Agar frontend portini o'zgartirmoqchi bo'lsam?
**A**: `docker-compose.yml` faylida `web.ports` qismini o'zgartiring:
```yaml
web:
  ports:
    - "YANGI_PORT:80"  # Masalan: "3000:80"
```

### Q: Container ichidagi port ham o'zgaradimi?
**A**: Yo'q! Container ichida Nginx har doim 80 portda ishlaydi. Faqat **host port** (global port) o'zgaradi.

### Q: FRONTEND_URL nima uchun kerak?
**A**: Backend CORS uchun ishlatadi - qaysi frontend'dan request qabul qilishni bilish uchun.

## Xulosa

✅ **Frontend global port: 2015** (docker-compose.yml)
✅ **API global port: 8000** (docker-compose.yml)
✅ **Web/.env**: Faqat API URL (backend bilan bog'lanish)
✅ **API/.env**: Backend URL + Frontend URL (CORS uchun)
