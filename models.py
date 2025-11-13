
import uuid
import json
from db import get_conn
from datetime import datetime,timezone

class Job:
    def __init__(self, id=None, command=None, max_retries=None):
        self.id = id or str(uuid.uuid4())
        self.command = command
        self.state = 'pending'
        self.attempts = 0
        self.max_retries = max_retries or 3
        self.next_retry_at = None
        self.output = None
        self.created_at = datetime.now(timezone.utc).isoformat() + "Z"
        self.updated_at = self.created_at

    @classmethod
    def from_json(cls, s):
        try:
            data = json.loads(s)
            if not data.get('command'):
                raise ValueError("Missing 'command'")
            return cls(
                id=data.get('id'),
                command=data['command'],
                max_retries=data.get('max_retries')
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Job validation failed: {e}")

    def save(self):
        conn = get_conn()
        conn.execute("""
            INSERT INTO jobs
            (id, command, state, attempts, max_retries, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (self.id, self.command, self.state, self.attempts,
              self.max_retries, self.created_at, self.updated_at))
        conn.commit()
        conn.close()
