from sqlalchemy import create_engine, inspect, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# SQLite optimizations for high concurrency
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {
        "check_same_thread": False,
        # Increase timeout for concurrent writes (200+ users)
        "timeout": 30,
        # Other SQLite optimizations
        "isolation_level": None,  # Autocommit mode for better concurrency
    }

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # Connection pool for better performance
    pool_size=20,  # Max 20 concurrent connections
    max_overflow=40,  # Up to 60 total connections under load
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections every hour
    echo=False  # Disable SQL logging for performance
)

# Enable WAL mode for SQLite (concurrent reads + single writer)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_conn.cursor()
        # WAL mode - allows concurrent reads while writing
        cursor.execute("PRAGMA journal_mode=WAL")
        # Optimize for speed over durability (safe for voting app)
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Increase cache size to 64MB
        cursor.execute("PRAGMA cache_size=-64000")
        # Memory-mapped I/O
        cursor.execute("PRAGMA mmap_size=268435456")
        # Temp store in memory
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

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

        def index_exists(index_name: str) -> bool:
            """Check if index exists in SQLite"""
            if dialect == "sqlite":
                result = connection.execute(text(
                    f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
                ))
                return result.fetchone() is not None
            return False

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

        # Create performance indexes for high concurrency
        if dialect == "sqlite":
            # Index for vote lookups (duplicate check)
            if not index_exists("idx_votes_event_candidate_ip"):
                connection.execute(text(
                    "CREATE INDEX idx_votes_event_candidate_ip ON votes(event_id, candidate_id, ip_address)"
                ))
                connection.commit()

            # Index for vote lookups with device_id
            if not index_exists("idx_votes_event_candidate_device"):
                connection.execute(text(
                    "CREATE INDEX idx_votes_event_candidate_device ON votes(event_id, candidate_id, device_id)"
                ))
                connection.commit()

            # Index for vote counting
            if not index_exists("idx_votes_event_candidate"):
                connection.execute(text(
                    "CREATE INDEX idx_votes_event_candidate ON votes(event_id, candidate_id, vote_type)"
                ))
                connection.commit()

            # Index for event candidates lookup
            if not index_exists("idx_event_candidates_event"):
                connection.execute(text(
                    'CREATE INDEX idx_event_candidates_event ON event_candidates(event_id, "order")'
                ))
                connection.commit()

            # Index for events by link (public access)
            if not index_exists("idx_events_link"):
                connection.execute(text(
                    "CREATE INDEX idx_events_link ON events(link)"
                ))
                connection.commit()
