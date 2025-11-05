"""
Initialize database with admin user
Run this script to create initial admin user
"""
from sqlalchemy.orm import Session
from .core.database import SessionLocal, engine, Base
from .core.security import get_password_hash
from .core.config import settings
from .models.admin import AdminUser


def init_db():
    """Initialize database with tables and admin user"""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = db.query(AdminUser).filter(
            AdminUser.username == settings.ADMIN_USERNAME
        ).first()

        if existing_admin:
            print(f"Admin user '{settings.ADMIN_USERNAME}' already exists")
            return

        # Create admin user
        admin = AdminUser(
            username=settings.ADMIN_USERNAME,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            is_active=True
        )
        db.add(admin)
        db.commit()

        print(f"✓ Admin user created successfully")
        print(f"  Username: {settings.ADMIN_USERNAME}")
        print(f"  Password: {settings.ADMIN_PASSWORD}")
        print(f"  Please change the password after first login!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
