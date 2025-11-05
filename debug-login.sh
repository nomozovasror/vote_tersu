#!/bin/bash

# Login Debug Script
# Bu script login muammosini aniqlash uchun

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Login Debug Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if container is running
log_info "1. Checking if container is running..."
if ! docker ps | grep -q voting_api; then
    log_error "voting_api container is not running!"
    exit 1
fi
log_info "✓ Container is running"
echo ""

# Check database exists
log_info "2. Checking if database exists..."
if docker exec voting_api test -f /app/data/voting.db; then
    log_info "✓ Database file exists"
else
    log_error "✗ Database file not found!"
    log_warn "Run: docker exec -it voting_api python -m app.init_db"
    exit 1
fi
echo ""

# Check admin users in database
log_info "3. Checking admin users in database..."
cat > /tmp/check_users.py << 'EOF'
import sys
sys.path.insert(0, '/app')

try:
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker
    from app.models.admin import AdminUser
    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Check if table exists
    inspector = inspect(engine)
    if 'admin_users' not in inspector.get_table_names():
        print("ERROR: admin_users table does not exist!")
        sys.exit(1)

    # Get all users
    users = db.query(AdminUser).all()
    if not users:
        print("ERROR: No admin users found in database!")
        sys.exit(1)

    print(f"Found {len(users)} admin user(s):")
    for user in users:
        print(f"  - ID: {user.id}, Username: {user.username}")
        print(f"    Password hash exists: {bool(user.hashed_password)}")
        print(f"    Hash length: {len(user.hashed_password) if user.hashed_password else 0}")

    db.close()

except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

docker cp /tmp/check_users.py voting_api:/tmp/check_users.py
RESULT=$(docker exec voting_api python /tmp/check_users.py 2>&1)
rm /tmp/check_users.py
docker exec voting_api rm /tmp/check_users.py

if echo "$RESULT" | grep -q "ERROR"; then
    log_error "$RESULT"
    echo ""
    log_warn "Try reinitializing database:"
    echo "  docker exec -it voting_api python -m app.init_db"
    exit 1
else
    echo "$RESULT"
fi
echo ""

# Test login with credentials
log_info "4. Testing login functionality..."
read -p "Enter username to test: " TEST_USERNAME
read -sp "Enter password to test: " TEST_PASSWORD
echo ""

cat > /tmp/test_login.py << EOF
import sys
sys.path.insert(0, '/app')

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.admin import AdminUser
    from app.core.security import verify_password
    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Find user
    user = db.query(AdminUser).filter(AdminUser.username == "$TEST_USERNAME").first()

    if not user:
        print("ERROR: User '$TEST_USERNAME' not found in database!")
        sys.exit(1)

    print(f"User found: {user.username}")
    print(f"User ID: {user.id}")
    print(f"Password hash length: {len(user.hashed_password)}")

    # Test password
    is_valid = verify_password("$TEST_PASSWORD", user.hashed_password)

    if is_valid:
        print("SUCCESS: Password is correct! ✓")
    else:
        print("ERROR: Password is incorrect! ✗")
        print("This means either:")
        print("  1. You entered wrong password")
        print("  2. Password hash in database is corrupted")
        print("  3. Password was set with different hashing algorithm")
        sys.exit(1)

    db.close()

except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

docker cp /tmp/test_login.py voting_api:/tmp/test_login.py
RESULT=$(docker exec voting_api python /tmp/test_login.py 2>&1)
rm /tmp/test_login.py
docker exec voting_api rm /tmp/test_login.py

echo ""
if echo "$RESULT" | grep -q "SUCCESS"; then
    log_info "$RESULT"
    echo ""
    log_info "Login test passed! ✓"
    echo ""
    log_info "If login still fails in browser:"
    echo "  1. Check browser console for errors (F12)"
    echo "  2. Check API URL in web/.env: VITE_API_URL=http://your-server-ip:2014"
    echo "  3. Check CORS settings in api/.env: FRONTEND_URL=http://your-server-ip:2013"
    echo "  4. Verify firewall allows ports 2013 & 2014: sudo ufw status"
    echo "  5. Check API logs: docker-compose logs -f api"
else
    log_error "$RESULT"
    echo ""
    log_warn "Password verification failed!"
    echo ""
    log_info "To reset password, run:"
    echo "  ./add-user.sh password"
fi
echo ""

# Check environment variables
log_info "5. Checking environment variables..."
cat > /tmp/check_env.py << 'EOF'
import sys
sys.path.insert(0, '/app')

try:
    from app.core.config import settings

    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"SECRET_KEY length: {len(settings.SECRET_KEY)}")
    print(f"SECRET_KEY set: {bool(settings.SECRET_KEY and settings.SECRET_KEY != 'your-secret-key-change-in-production')}")
    print(f"ALGORITHM: {settings.ALGORITHM}")
    print(f"FRONTEND_URL: {settings.FRONTEND_URL}")

except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
EOF

docker cp /tmp/check_env.py voting_api:/tmp/check_env.py
docker exec voting_api python /tmp/check_env.py
rm /tmp/check_env.py
docker exec voting_api rm /tmp/check_env.py
echo ""

# Check API accessibility
log_info "6. Checking API accessibility..."
echo "Testing API endpoint..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:2013/docs | grep -q "200"; then
    log_info "✓ API is accessible on port 2013"
else
    log_error "✗ API is not accessible on port 2013"
    log_warn "Check if port mapping is correct in docker-compose.yml"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Debug Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
log_info "If all checks pass but login still fails:"
echo "  1. Clear browser cache and cookies"
echo "  2. Try incognito/private window"
echo "  3. Check network tab in browser DevTools (F12)"
echo "  4. Verify API URL matches: http://your-server-ip:2013"
echo "  5. Check docker logs: docker-compose logs -f api"
echo ""
