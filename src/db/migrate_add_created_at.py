"""
Migration: Add missing columns to accounts table and create accounts_status table
PostgreSQL version
"""
from config import db, sql


def create_accounts_status_table():
    """Create accounts_status table for daily statistics"""
    try:
        sql.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'accounts_status'
        """)
        
        if not sql.fetchone():
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
        db.rollback()
        print(f"[MIGRATION ERROR] accounts_status: {e}")
        return False


def add_missing_columns_to_accounts():
    """Add missing columns to accounts table if they don't exist"""
    columns_to_add = [
        ('created_at', 'TIMESTAMP DEFAULT now()'),
        ('updated_at', 'TIMESTAMP DEFAULT now()'),
        ('first_name', 'VARCHAR(255)'),
        ('username', 'VARCHAR(100)'),
        ('is_blocked', 'BOOLEAN DEFAULT FALSE')
    ]
    
    try:
        for col_name, col_type in columns_to_add:
            sql.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'accounts' AND column_name = %s
            """, (col_name,))
            
            if not sql.fetchone():
                print(f"[MIGRATION] Adding {col_name} column to accounts table...")
                sql.execute(f"""
                    ALTER TABLE accounts 
                    ADD COLUMN {col_name} {col_type}
                """)
                db.commit()
                print(f"[MIGRATION] {col_name} column added successfully!")
            else:
                print(f"[MIGRATION] {col_name} column already exists in accounts table")
            
        return True
        
    except Exception as e:
        db.rollback()
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
