# Stress Test Quick Reference

## ⚡ Quick Commands

```bash
# Dependencies o'rnatish (faqat bir marta)
pip install -r stress_test_requirements.txt

# Event link olish (Admin paneldan)
# 1. http://localhost:2013/admin/login
# 2. Create Event → Copy event link

# Tez testlar
./quick_test.sh <event-link> small   # 50 users, 30s
./quick_test.sh <event-link> medium  # 100 users, 60s
./quick_test.sh <event-link> large   # 200 users, 120s

# Real-time monitoring
python3 monitor.py --api http://localhost:2014

# Stats tekshirish
curl http://localhost:2014/ws-stats | jq
```

## 📊 Test Types

| Command | Users | Duration | Maqsad |
|---------|-------|----------|--------|
| `small` | 50 | 30s | Tezkor test |
| `medium` | 100 | 60s | Standart test |
| `large` | 200 | 120s | Full capacity |
| `extreme` | 500 | 60s | Limit topish |
| `ramp` | 200 | 180s | Gradual load |
| `vote` | 100 | 60s | Ovoz bilan test |

## 🎯 Custom Test

```bash
python3 stress_test.py \
    --api http://localhost:2014 \
    --link <event-link> \
    --users 150 \
    --duration 90 \
    --batch-size 50 \
    --vote  # optional: enable voting
```

## 📈 Success Criteria

| Metric | Good | Warning | Bad |
|--------|------|---------|-----|
| Success Rate | ≥95% | 80-95% | <80% |
| Connection Time | <1s | 1-2s | >2s |
| Vote Time | <500ms | 500ms-1s | >1s |

## 🔍 Monitoring During Test

**Terminal 1:** Run test
```bash
./quick_test.sh <link> large
```

**Terminal 2:** Monitor
```bash
python3 monitor.py
```

**Terminal 3:** Watch stats
```bash
watch -n 1 'curl -s http://localhost:2014/ws-stats | jq'
```

## 🐛 Troubleshooting

### Test yuklana olmayapti
```bash
pip install --upgrade websockets aiohttp psutil
```

### "Connection refused"
```bash
docker ps | grep voting
docker-compose restart
curl http://localhost:2014/health
```

### 30-40 userdan keyin fail
```bash
# Check ulimits
docker exec voting_api sh -c "ulimit -n"
# Should be: 65536

# If 1024, fix:
docker-compose down
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

### High CPU/Memory
```bash
# Check stats
curl http://localhost:2014/ws-stats

# Monitor resources
docker stats voting_api

# Check logs
docker logs voting_api --tail 50
```

## 📝 Example Session

```bash
# 1. Start server
docker-compose up -d

# 2. Get event link from admin panel
# http://localhost:2013/admin/login

# 3. Run baseline test
./quick_test.sh abc-123-def small

# 4. If passed, scale up
./quick_test.sh abc-123-def medium

# 5. If passed, full test
./quick_test.sh abc-123-def large

# 6. Monitor results
python3 monitor.py
```

## 🎓 Test Scenarios

### Scenario 1: Quick Health Check
```bash
./quick_test.sh <link> small
# Expected: 95%+ success in ~30s
```

### Scenario 2: Production Readiness
```bash
./quick_test.sh <link> large
# Expected: 200 users, 95%+ success
```

### Scenario 3: Find Breaking Point
```bash
for users in 50 100 150 200 250 300; do
  python3 stress_test.py --api http://localhost:2014 \
    --link <link> --users $users --duration 30
  sleep 5
done
```

### Scenario 4: Real-world Simulation
```bash
# Ramp up slowly (users joining)
python3 stress_test.py --api http://localhost:2014 \
  --link <link> --mode ramp \
  --max-users 200 --ramp-time 120 --hold-time 180
```

## 📊 Reading Results

```
======================================================================
STRESS TEST NATIJALAR
======================================================================

📡 CONNECTION STATISTICS:
  Total attempts:      200
  ✅ Successful:        198 (99.00%)  ← Good! >95%
  ❌ Failed:            2 (1.00%)     ← Acceptable <5%

  Connection timing:
    Average: 0.156s   ← Good! <1s
    Max:     0.245s   ← Good! <2s

⚡ PERFORMANCE:
  Test duration:       122.45s
  Connections/sec:     1.63

======================================================================
✅ TEST PASSED - Success rate: 99.00%
======================================================================
```

**Interpretation:**
- ✅ **PASSED**: Success ≥95%, times <1s → Production ready
- ⚠️  **WARNING**: Success 80-95% → Investigate, may work with optimization
- ❌ **FAILED**: Success <80% → Fix required before production

## 🔗 Full Docs

- **STRESS_TEST_GUIDE.md** - Complete testing documentation
- **PERFORMANCE.md** - Scaling & optimization guide
- **SETUP_GUIDE.md** - Production deployment

## 💡 Pro Tips

1. **Always test with more users than expected**
   - If expecting 150 users, test with 200-250

2. **Test in stages**
   - small → medium → large (don't jump to extreme)

3. **Monitor during tests**
   - Use `monitor.py` in separate terminal

4. **Save test results**
   ```bash
   ./quick_test.sh <link> large 2>&1 | tee test_$(date +%Y%m%d_%H%M%S).log
   ```

5. **Test with voting enabled for real simulation**
   ```bash
   ./quick_test.sh <link> vote
   ```

6. **Don't test on production!**
   - Always use development or staging environment
