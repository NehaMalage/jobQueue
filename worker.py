from db import get_conn
from utils import calculate_backoff
from datetime import datetime, timedelta, timezone
import subprocess

def pick_and_lock_job():
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute("""
        SELECT * FROM jobs WHERE state IN ('pending', 'failed')
        AND (next_retry_at IS NULL OR next_retry_at <= ?)
        ORDER BY created_at ASC LIMIT 1
    """, (now,)).fetchone()
    if row:
        conn.execute("UPDATE jobs SET state='processing' WHERE id=?", (row['id'],))
        conn.commit()
        conn.close()
        return dict(row)
    conn.close()
    return None

def complete_job(job_id, output):
    conn = get_conn()
    conn.execute("UPDATE jobs SET state='completed', output=?, updated_at=? WHERE id=?",
                 (output[:1000], datetime.now(timezone.utc).isoformat() + "Z", job_id))
    conn.commit()
    conn.close()

def fail_job(job):
    conn = get_conn()
    attempts = job['attempts'] + 1
    max_retries = job['max_retries']
    if attempts >= max_retries:
        conn.execute("UPDATE jobs SET state='dead', attempts=?, output=?, updated_at=? WHERE id=?",
                     (attempts, f"Failed after {attempts} attempts",
                      datetime.now(timezone.utc).isoformat() + "Z", job['id']))
    else:
        delay = calculate_backoff(attempts)
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        conn.execute("UPDATE jobs SET state='failed', attempts=?, next_retry_at=?, updated_at=? WHERE id=?",
                     (attempts, retry_at.isoformat() + "Z",
                      datetime.now(timezone.utc).isoformat() + "Z", job['id']))
    conn.commit()
    conn.close()

def execute_job(job):
    try:
        result = subprocess.run(job['command'], shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            complete_job(job['id'], result.stdout)
        else:
            fail_job(job)
    except:
        fail_job(job)
