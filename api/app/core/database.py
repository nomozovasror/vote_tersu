from sqlalchemy import create_engine, inspect, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

is_sqlite = "sqlite" in settings.DATABASE_URL

if is_sqlite:
    connect_args = {
        "check_same_thread": False,
        "timeout": 30,
        "isolation_level": None,
    }
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
else:
    # PostgreSQL
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=50,
        max_overflow=150,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=60,
        echo=False,
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
        def table_columns(table_name: str):
            if is_sqlite:
                result = connection.execute(text(f"PRAGMA table_info('{table_name}')"))
                return [row[1] for row in result]
            else:
                result = connection.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :tbl"
                ), {"tbl": table_name})
                return [row[0] for row in result]

        def index_exists(index_name: str) -> bool:
            if is_sqlite:
                result = connection.execute(text(
                    f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
                ))
                return result.fetchone() is not None
            else:
                result = connection.execute(text(
                    "SELECT 1 FROM pg_indexes WHERE indexname = :idx"
                ), {"idx": index_name})
                return result.fetchone() is not None

        # Ensure timer_started_at exists on event_candidates
        event_candidate_columns = table_columns("event_candidates")
        if event_candidate_columns and "timer_started_at" not in event_candidate_columns:
            connection.execute(text(
                "ALTER TABLE event_candidates ADD COLUMN timer_started_at TIMESTAMP"
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
            connection.execute(text(
                "UPDATE candidates SET which_position = position WHERE which_position IS NULL OR which_position = ''"
            ))
            connection.commit()

        # Ensure device_id exists on votes
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

        # Create performance indexes
        if not index_exists("idx_votes_event_candidate_ip"):
            connection.execute(text(
                "CREATE INDEX idx_votes_event_candidate_ip ON votes(event_id, candidate_id, ip_address)"
            ))
            connection.commit()

        if not index_exists("idx_votes_event_candidate_device"):
            connection.execute(text(
                "CREATE INDEX idx_votes_event_candidate_device ON votes(event_id, candidate_id, device_id)"
            ))
            connection.commit()

        if not index_exists("idx_votes_event_candidate"):
            connection.execute(text(
                "CREATE INDEX idx_votes_event_candidate ON votes(event_id, candidate_id, vote_type)"
            ))
            connection.commit()

        if not index_exists("idx_event_candidates_event"):
            if is_sqlite:
                connection.execute(text(
                    'CREATE INDEX idx_event_candidates_event ON event_candidates(event_id, "order")'
                ))
            else:
                connection.execute(text(
                    'CREATE INDEX idx_event_candidates_event ON event_candidates(event_id, "order")'
                ))
            connection.commit()

        if not index_exists("idx_events_link"):
            connection.execute(text(
                "CREATE INDEX idx_events_link ON events(link)"
            ))
            connection.commit()
