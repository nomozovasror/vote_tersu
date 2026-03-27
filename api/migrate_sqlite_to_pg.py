"""
Migrate data from SQLite to PostgreSQL.

Usage (inside Docker after PostgreSQL is running):
    python migrate_sqlite_to_pg.py /app/data/voting.db

Or locally:
    DATABASE_URL=postgresql://voting:voting_secret@localhost:5432/voting \
    python migrate_sqlite_to_pg.py ../data/voting.db

To force re-migrate (clear PG tables first):
    python migrate_sqlite_to_pg.py /app/data/voting.db --force
"""
import sys
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base


def migrate(sqlite_path: str, force: bool = False):
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()

    # Connect to PostgreSQL
    pg_engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=pg_engine)
    PgSession = sessionmaker(bind=pg_engine)
    pg = PgSession()

    # Migration order matters (foreign key dependencies)
    tables = [
        "admin_users",
        "candidates",
        "events",
        "event_candidates",
        "votes",
        "display_states",
    ]

    # Reverse order for deletion (respect foreign keys)
    if force:
        print("Force mode: clearing PostgreSQL tables...")
        for table in reversed(tables):
            pg.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        pg.commit()
        print("Tables cleared.\n")

    try:
        for table in tables:
            print(f"\n--- {table} ---")

            # Check if target table already has data
            result = pg.execute(text(f"SELECT COUNT(*) FROM {table}"))
            existing_count = result.scalar()
            if existing_count > 0:
                print(f"  Skipping: already has {existing_count} rows")
                continue

            # Read from SQLite
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            if not rows:
                print(f"  Empty table, skipping")
                continue

            columns = [desc[0] for desc in cursor.description]
            print(f"  Rows to migrate: {len(rows)}")

            # Detect boolean columns from PostgreSQL schema
            bool_cols_result = pg.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :tbl AND data_type = 'boolean'"
            ), {"tbl": table})
            bool_columns = {r[0] for r in bool_cols_result}
            if bool_columns:
                print(f"  Boolean columns: {bool_columns}")

            col_names = ", ".join([f'"{col}"' for col in columns])
            placeholders = ", ".join([
                f"CAST(:{col} AS boolean)" if col in bool_columns else f":{col}"
                for col in columns
            ])
            sql = f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})'

            migrated = 0
            for row in rows:
                d = dict(row)
                pg.execute(text(sql), d)
                migrated += 1

                if migrated % 500 == 0:
                    pg.commit()
                    print(f"  Migrated {migrated}/{len(rows)}")

            pg.commit()
            print(f"  Migrated {migrated}/{len(rows)}")

            # Reset PostgreSQL sequence to max id
            result = pg.execute(text(f"SELECT MAX(id) FROM {table}"))
            max_id = result.scalar()
            if max_id:
                seq_name = f"{table}_id_seq"
                try:
                    pg.execute(text(f"SELECT setval('{seq_name}', {max_id})"))
                    pg.commit()
                    print(f"  Sequence {seq_name} set to {max_id}")
                except Exception as e:
                    pg.rollback()
                    print(f"  Sequence reset skipped: {e}")

        print("\n" + "=" * 50)
        print("Migration completed successfully!")
        print("=" * 50)

        # Verify counts
        print("\nVerification:")
        for table in tables:
            sqlite_count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            pg_count = pg.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            status = "OK" if sqlite_count == pg_count else "MISMATCH"
            print(f"  {table}: SQLite={sqlite_count} PostgreSQL={pg_count} [{status}]")

    except Exception as e:
        pg.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        pg.close()
        sqlite_conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate_sqlite_to_pg.py <sqlite_db_path> [--force]")
        print("Example: python migrate_sqlite_to_pg.py /app/data/voting.db")
        sys.exit(1)

    sqlite_path = sys.argv[1]
    force = "--force" in sys.argv
    print(f"Migrating from: {sqlite_path}")
    print(f"Migrating to: {settings.DATABASE_URL}")
    migrate(sqlite_path, force=force)
