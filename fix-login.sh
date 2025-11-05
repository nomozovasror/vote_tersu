#!/bin/bash

# Quick Login Fix Script
# Bu script login muammosini tezda hal qilish uchun

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
echo -e "${BLUE}Quick Login Fix${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check container
if ! docker ps | grep -q voting_api; then
    log_error "voting_api container is not running!"
    log_info "Starting containers..."
    docker-compose up -d
    sleep 5
fi

log_info "This script will:"
echo "  1. Reinitialize the database"
echo "  2. Create new admin user"
echo "  3. Restart containers"
echo ""

read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    log_warn "Cancelled."
    exit 0
fi

echo ""
log_info "Step 1: Backing up current database..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -f "data/voting.db" ]; then
    mkdir -p backups
    cp data/voting.db "backups/voting_backup_$TIMESTAMP.db"
    log_info "✓ Backup created: backups/voting_backup_$TIMESTAMP.db"
else
    log_warn "No existing database found"
fi

echo ""
log_info "Step 2: Reinitializing database..."
docker exec voting_api python -m app.init_db

echo ""
log_info "Step 3: Creating admin user..."
read -p "Enter admin username (default: admin): " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

while true; do
    read -sp "Enter admin password: " ADMIN_PASS
    echo ""
    read -sp "Confirm password: " ADMIN_PASS_CONFIRM
    echo ""

    if [ "$ADMIN_PASS" = "$ADMIN_PASS_CONFIRM" ]; then
        break
    else
        log_error "Passwords do not match! Try again."
    fi
done

# Create admin user
cat > /tmp/create_admin.py << EOF
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.admin import AdminUser
from app.core.security import get_password_hash
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Remove existing user if exists
    existing = db.query(AdminUser).filter(AdminUser.username == "$ADMIN_USER").first()
    if existing:
        db.delete(existing)
        db.commit()

    # Create new user
    hashed_password = get_password_hash("$ADMIN_PASS")
    new_user = AdminUser(
        username="$ADMIN_USER",
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    print(f"SUCCESS: Admin user '$ADMIN_USER' created!")

except Exception as e:
    print(f"ERROR: {str(e)}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
EOF

docker cp /tmp/create_admin.py voting_api:/tmp/create_admin.py
RESULT=$(docker exec voting_api python /tmp/create_admin.py)
rm /tmp/create_admin.py
docker exec voting_api rm /tmp/create_admin.py

echo ""
if echo "$RESULT" | grep -q "SUCCESS"; then
    log_info "$RESULT"
else
    log_error "$RESULT"
    exit 1
fi

echo ""
log_info "Step 4: Restarting containers..."
docker-compose restart

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Login Fixed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Admin Credentials:${NC}"
echo "  Username: $ADMIN_USER"
echo "  Password: ********"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  Admin Panel: http://localhost:2013/admin/login"
echo "  API Docs: http://localhost:2014/docs"
echo ""
log_info "Try logging in now!"
echo ""
