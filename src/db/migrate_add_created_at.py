"""
Migration: Add missing columns to accounts table and create accounts_status table
SQLite + PostgreSQL compatible version
"""
from config import db, sql, DB_TYPE


def _table_exists(table_name):
    """Check if a table exists — works for both SQLite and PostgreSQL"""
    try:
        if DB_TYPE == "sqlite":
            sql.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table_name,))
        else:
            sql.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name=%s",
                (table_name,))
        return sql.fetchone() is not None
    except Exception:
        return False


def _column_exists(table_name, column_name):
    """Check if a column exists in a table — works for both SQLite and PostgreSQL"""
    try:
        if DB_TYPE == "sqlite":
            sql.execute(f"PRAGMA table_info({table_name})")
            rows = sql.fetchall()
            return any(str(row[1]) == column_name for row in rows)
        else:
            sql.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=%s AND column_name=%s",
                (table_name, column_name))
            return sql.fetchone() is not None
    except Exception:
        return False


def create_accounts_status_table():
    """Create accounts_status table for daily statistics"""
    try:
        if not _table_exists('accounts_status'):
            print("[MIGRATION] Creating accounts_status table...")
            sql.execute("""
                CREATE TABLE IF NOT EXISTS accounts_status (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    date DATE DEFAULT CURRENT_DATE,
                    UNIQUE(user_id, date)
                )
            """)
            db.commit()
            print("[MIGRATION] accounts_status table created successfully!")
        else:
            print("[MIGRATION] accounts_status table already exists")
        return True
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[MIGRATION ERROR] accounts_status: {e}")
        return False


def add_missing_columns_to_accounts():
    """Add missing columns to accounts table if they don't exist"""
    if not _table_exists('accounts'):
        print("[MIGRATION] accounts table does not exist yet, skipping")
        return True

    is_sqlite = (DB_TYPE == "sqlite")
    columns_to_add = [
        ('created_at',  'TEXT DEFAULT CURRENT_TIMESTAMP' if is_sqlite else 'TIMESTAMP DEFAULT now()'),
        ('updated_at',  'TEXT DEFAULT CURRENT_TIMESTAMP' if is_sqlite else 'TIMESTAMP DEFAULT now()'),
        ('first_name',  'TEXT'),
        ('username',    'TEXT'),
        ('is_blocked',  'INTEGER DEFAULT 0'            if is_sqlite else 'BOOLEAN DEFAULT FALSE'),
    ]

    try:
        for col_name, col_type in columns_to_add:
            if not _column_exists('accounts', col_name):
                print(f"[MIGRATION] Adding {col_name} to accounts...")
                sql.execute(f"ALTER TABLE accounts ADD COLUMN {col_name} {col_type}")
                db.commit()
                print(f"[MIGRATION] {col_name} added.")
            else:
                print(f"[MIGRATION] {col_name} already exists.")
        return True
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[MIGRATION ERROR] {e}")
        return False


def run_all_migrations():
    """Run all migrations"""
    print("[MIGRATION] Starting database migrations...")
    add_missing_columns_to_accounts()
    create_accounts_status_table()
    print("[MIGRATION] All migrations completed!")


if __name__ == "__main__":
    run_all_migrations()
