import sqlite3
from datetime import datetime

DB_FILE = "queue.db"

def get_conn():
    """Get a database connection with Row factory for dict-like access"""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
   
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Initialize database schema and default configuration"""
    conn = get_conn()
    
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            state TEXT DEFAULT 'pending',
            attempts INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            next_retry_at TEXT,
            output TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
   
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_state_retry 
        ON jobs(state, next_retry_at, created_at)
    """)
    
   
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
   
    conn.execute("INSERT OR IGNORE INTO config VALUES ('max_retries', '3')")
    conn.execute("INSERT OR IGNORE INTO config VALUES ('backoff_base', '2')")
    
    conn.commit()
    conn.close()
