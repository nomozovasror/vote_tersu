from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # University Info
    UNIVERSITY_NAME: str = "University"
    UNIVERSITY_SHORT_NAME: str = "UNI"

    # Database
    DATABASE_URL: str = "sqlite:///./data/voting.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # External API (HEMIS)
    EXTERNAL_API_URL: str = "https://student.tersu.uz/rest/v1/data/employee-list"
    EXTERNAL_API_TOKEN: str = ""

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Backend URL for image paths
    BACKEND_URL: str = "http://localhost:8000"

    # Server configuration
    SERVER_HOST: str = "localhost"
    API_PORT: int = 2014
    WEB_PORT: int = 2013

    # Performance settings
    WEB_CONCURRENCY: int = 6
    MAX_CONNECTIONS_PER_EVENT: int = 500
    MAX_TOTAL_CONNECTIONS: int = 2000

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
