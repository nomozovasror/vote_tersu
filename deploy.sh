#!/bin/bash

# Voting App Production Deployment Script
# Usage: ./deploy.sh [start|stop|restart|update|backup|logs]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    log_info "All requirements met."
}

check_env_files() {
    log_info "Checking environment files..."

    if [ ! -f "api/.env" ]; then
        log_error "api/.env file not found!"
        log_warn "Please create api/.env file. See DEPLOY.md for details."
        exit 1
    fi

    if [ ! -f "web/.env" ]; then
        log_error "web/.env file not found!"
        log_warn "Please create web/.env file. See DEPLOY.md for details."
        exit 1
    fi

    # Check if default passwords are changed
    if grep -q "admin123" api/.env; then
        log_warn "WARNING: Default admin password detected in api/.env"
        log_warn "Please change ADMIN_PASSWORD in api/.env for security!"
    fi

    log_info "Environment files OK."
}

start_app() {
    log_info "Starting Voting App..."
    check_requirements
    check_env_files

    # Create data directory if not exists
    mkdir -p data

    # Use production compose file if exists, otherwise use default
    if [ -f "docker-compose.prod.yml" ]; then
        docker-compose -f docker-compose.prod.yml up -d --build
    else
        docker-compose up -d --build
    fi

    log_info "Waiting for containers to be healthy..."
    sleep 5

    # Initialize database if not exists
    if [ ! -f "data/voting.db" ]; then
        log_info "Initializing database..."
        docker exec -it voting_api python -m app.init_db
    fi

    log_info "Voting App started successfully!"
    log_info "Frontend: http://localhost:2013"
    log_info "API: http://localhost:2014"
    log_info "API Docs: http://localhost:2014/docs"
}

stop_app() {
    log_info "Stopping Voting App..."

    if [ -f "docker-compose.prod.yml" ]; then
        docker-compose -f docker-compose.prod.yml down
    else
        docker-compose down
    fi

    log_info "Voting App stopped."
}

restart_app() {
    log_info "Restarting Voting App..."
    stop_app
    sleep 2
    start_app
}

update_app() {
    log_info "Updating Voting App..."

    # Pull latest code if git repo
    if [ -d ".git" ]; then
        log_info "Pulling latest code from git..."
        git pull
    fi

    # Backup database before update
    backup_db

    # Rebuild and restart
    log_info "Rebuilding containers..."
    if [ -f "docker-compose.prod.yml" ]; then
        docker-compose -f docker-compose.prod.yml down
        docker-compose -f docker-compose.prod.yml up -d --build
    else
        docker-compose down
        docker-compose up -d --build
    fi

    log_info "Update completed!"
}

backup_db() {
    log_info "Creating database backup..."

    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/voting_backup_$TIMESTAMP.db"

    if [ -f "data/voting.db" ]; then
        cp data/voting.db "$BACKUP_FILE"
        log_info "Backup created: $BACKUP_FILE"

        # Keep only last 10 backups
        cd "$BACKUP_DIR"
        ls -t voting_backup_*.db | tail -n +11 | xargs rm -f 2>/dev/null || true
        cd "$SCRIPT_DIR"

        log_info "Old backups cleaned up (keeping last 10)."
    else
        log_warn "No database file found to backup."
    fi
}

view_logs() {
    log_info "Showing logs (Ctrl+C to exit)..."

    if [ -f "docker-compose.prod.yml" ]; then
        docker-compose -f docker-compose.prod.yml logs -f
    else
        docker-compose logs -f
    fi
}

show_status() {
    log_info "Container Status:"
    docker-compose ps

    echo ""
    log_info "Resource Usage:"
    docker stats --no-stream voting_api voting_web

    echo ""
    log_info "Disk Usage:"
    df -h data/ 2>/dev/null || echo "Data directory not found"
}

show_usage() {
    cat << EOF
Voting App Deployment Script

Usage: $0 [command]

Commands:
    start       Start the application
    stop        Stop the application
    restart     Restart the application
    update      Update and rebuild the application
    backup      Backup the database
    logs        View application logs
    status      Show application status
    help        Show this help message

Examples:
    $0 start
    $0 logs
    $0 backup

EOF
}

# Main
case "${1:-}" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    update)
        update_app
        ;;
    backup)
        backup_db
        ;;
    logs)
        view_logs
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        log_error "Invalid command: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac
