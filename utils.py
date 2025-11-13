
from db import get_conn
from datetime import datetime, timedelta
import math

def get_config(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_config(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO config VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def calculate_backoff(attempts):
    base = int(get_config('backoff_base', 2))
    return base ** attempts
