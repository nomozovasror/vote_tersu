from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """Lightweight migration hooks for incremental schema updates."""
    with engine.connect() as connection:
        dialect = engine.dialect.name

        inspector = inspect(connection) if dialect != "sqlite" else None

        def table_columns(table_name: str):
            if dialect == "sqlite":
                result = connection.execute(text(f"PRAGMA table_info('{table_name}')"))
                return [row[1] for row in result]  # (cid, name, type, ...)
            if inspector:
                try:
                    return [col["name"] for col in inspector.get_columns(table_name)]
                except Exception:
                    return []
            return []

        # Ensure timer_started_at exists on event_candidates
        event_candidate_columns = table_columns("event_candidates")
        if event_candidate_columns and "timer_started_at" not in event_candidate_columns:
            connection.execute(text(
                "ALTER TABLE event_candidates ADD COLUMN timer_started_at DATETIME"
            ))
            connection.commit()

        # Ensure candidate_group exists on event_candidates
        event_candidate_columns = table_columns("event_candidates")
        if event_candidate_columns and "candidate_group" not in event_candidate_columns:
            connection.execute(text(
                "ALTER TABLE event_candidates ADD COLUMN candidate_group VARCHAR"
            ))
            connection.commit()

        # Ensure which_position exists on candidates
        candidate_columns = table_columns("candidates")
        if candidate_columns and "which_position" not in candidate_columns:
            connection.execute(text(
                "ALTER TABLE candidates ADD COLUMN which_position VARCHAR"
            ))
            # Pre-fill new column with legacy position values
            connection.execute(text(
                "UPDATE candidates SET which_position = position WHERE which_position IS NULL OR which_position = ''"
            ))
            connection.commit()

        # Ensure device_id exists on votes (for multi-device voting on same WiFi)
        vote_columns = table_columns("votes")
        if vote_columns and "device_id" not in vote_columns:
            connection.execute(text(
                "ALTER TABLE votes ADD COLUMN device_id VARCHAR"
            ))
            connection.commit()

        # Ensure participant_count exists on event_candidates
        event_candidate_columns = table_columns("event_candidates")
        if event_candidate_columns and "participant_count" not in event_candidate_columns:
            connection.execute(text(
                "ALTER TABLE event_candidates ADD COLUMN participant_count INTEGER DEFAULT 0"
            ))
            connection.commit()
