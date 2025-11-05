#!/bin/bash

# Admin User Management Script
# Usage: ./add-user.sh [add|list|delete]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if container is running
check_container() {
    if ! docker ps | grep -q voting_api; then
        log_error "voting_api container is not running!"
        log_warn "Please start the application first: docker-compose up -d"
        exit 1
    fi
}

# Add new admin user
add_user() {
    log_info "Adding new admin user..."
    echo ""

    # Get username
    read -p "Enter username: " USERNAME
    if [ -z "$USERNAME" ]; then
        log_error "Username cannot be empty!"
        exit 1
    fi

    # Get password
    while true; do
        read -sp "Enter password: " PASSWORD
        echo ""
        read -sp "Confirm password: " PASSWORD_CONFIRM
        echo ""

        if [ "$PASSWORD" = "$PASSWORD_CONFIRM" ]; then
            break
        else
            log_error "Passwords do not match! Please try again."
        fi
    done

    if [ -z "$PASSWORD" ]; then
        log_error "Password cannot be empty!"
        exit 1
    fi

    # Create Python script to add user
    cat > /tmp/add_admin_user.py << EOF
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.admin import AdminUser
from app.core.security import get_password_hash
from app.core.config import settings

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Check if user already exists
    existing = db.query(AdminUser).filter(AdminUser.username == "$USERNAME").first()
    if existing:
        print("ERROR: User '$USERNAME' already exists!")
        sys.exit(1)

    # Create new user
    hashed_password = get_password_hash("$PASSWORD")
    new_user = AdminUser(
        username="$USERNAME",
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    print(f"SUCCESS: Admin user '$USERNAME' created successfully!")

except Exception as e:
    print(f"ERROR: {str(e)}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
EOF

    # Copy script to container and execute
    docker cp /tmp/add_admin_user.py voting_api:/tmp/add_admin_user.py
    RESULT=$(docker exec voting_api python /tmp/add_admin_user.py)

    # Clean up
    rm /tmp/add_admin_user.py
    docker exec voting_api rm /tmp/add_admin_user.py

    # Check result
    if echo "$RESULT" | grep -q "SUCCESS"; then
        echo ""
        log_info "$RESULT"
        echo ""
        log_info "User credentials:"
        echo -e "  ${BLUE}Username:${NC} $USERNAME"
        echo -e "  ${BLUE}Password:${NC} ********"
        echo ""
    else
        echo ""
        log_error "$RESULT"
        exit 1
    fi
}

# List all admin users
list_users() {
    log_info "Admin users list:"
    echo ""

    cat > /tmp/list_admin_users.py << EOF
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.admin import AdminUser
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    users = db.query(AdminUser).all()
    if not users:
        print("No admin users found.")
    else:
        print(f"{'ID':<5} {'Username':<20} {'Created At':<25}")
        print("-" * 50)
        for user in users:
            created = user.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(user, 'created_at') and user.created_at else "N/A"
            print(f"{user.id:<5} {user.username:<20} {created:<25}")
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
finally:
    db.close()
EOF

    docker cp /tmp/list_admin_users.py voting_api:/tmp/list_admin_users.py
    docker exec voting_api python /tmp/list_admin_users.py

    rm /tmp/list_admin_users.py
    docker exec voting_api rm /tmp/list_admin_users.py
    echo ""
}

# Delete admin user
delete_user() {
    log_info "Delete admin user"
    echo ""

    # First list users
    list_users

    read -p "Enter username to delete: " USERNAME
    if [ -z "$USERNAME" ]; then
        log_error "Username cannot be empty!"
        exit 1
    fi

    # Confirm deletion
    read -p "Are you sure you want to delete user '$USERNAME'? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log_warn "Deletion cancelled."
        exit 0
    fi

    cat > /tmp/delete_admin_user.py << EOF
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.admin import AdminUser
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    user = db.query(AdminUser).filter(AdminUser.username == "$USERNAME").first()
    if not user:
        print("ERROR: User '$USERNAME' not found!")
        sys.exit(1)

    db.delete(user)
    db.commit()
    print(f"SUCCESS: User '$USERNAME' deleted successfully!")

except Exception as e:
    print(f"ERROR: {str(e)}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
EOF

    docker cp /tmp/delete_admin_user.py voting_api:/tmp/delete_admin_user.py
    RESULT=$(docker exec voting_api python /tmp/delete_admin_user.py)

    rm /tmp/delete_admin_user.py
    docker exec voting_api rm /tmp/delete_admin_user.py

    echo ""
    if echo "$RESULT" | grep -q "SUCCESS"; then
        log_info "$RESULT"
    else
        log_error "$RESULT"
        exit 1
    fi
}

# Change password
change_password() {
    log_info "Change admin user password"
    echo ""

    # First list users
    list_users

    read -p "Enter username: " USERNAME
    if [ -z "$USERNAME" ]; then
        log_error "Username cannot be empty!"
        exit 1
    fi

    # Get new password
    while true; do
        read -sp "Enter new password: " PASSWORD
        echo ""
        read -sp "Confirm new password: " PASSWORD_CONFIRM
        echo ""

        if [ "$PASSWORD" = "$PASSWORD_CONFIRM" ]; then
            break
        else
            log_error "Passwords do not match! Please try again."
        fi
    done

    if [ -z "$PASSWORD" ]; then
        log_error "Password cannot be empty!"
        exit 1
    fi

    cat > /tmp/change_password.py << EOF
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
    user = db.query(AdminUser).filter(AdminUser.username == "$USERNAME").first()
    if not user:
        print("ERROR: User '$USERNAME' not found!")
        sys.exit(1)

    user.hashed_password = get_password_hash("$PASSWORD")
    db.commit()
    print(f"SUCCESS: Password for user '$USERNAME' changed successfully!")

except Exception as e:
    print(f"ERROR: {str(e)}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
EOF

    docker cp /tmp/change_password.py voting_api:/tmp/change_password.py
    RESULT=$(docker exec voting_api python /tmp/change_password.py)

    rm /tmp/change_password.py
    docker exec voting_api rm /tmp/change_password.py

    echo ""
    if echo "$RESULT" | grep -q "SUCCESS"; then
        log_info "$RESULT"
    else
        log_error "$RESULT"
        exit 1
    fi
}

# Show usage
show_usage() {
    cat << EOF
${GREEN}Admin User Management Script${NC}

Usage: $0 [command]

Commands:
    add         Add new admin user
    list        List all admin users
    delete      Delete admin user
    password    Change user password
    help        Show this help message

Examples:
    $0 add
    $0 list
    $0 delete
    $0 password

EOF
}

# Main
check_container

case "${1:-}" in
    add)
        add_user
        ;;
    list)
        list_users
        ;;
    delete)
        delete_user
        ;;
    password|passwd)
        change_password
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        if [ -z "${1:-}" ]; then
            log_error "No command specified"
        else
            log_error "Invalid command: ${1}"
        fi
        echo ""
        show_usage
        exit 1
        ;;
esac
