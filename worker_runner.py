#!/usr/bin/env python3
"""
Standalone worker process runner.
This script is called by queuectl.py to run background workers.
"""
import time
import sys
from pathlib import Path
from worker import pick_and_lock_job, execute_job

STOP_FILE = "queuectl.stop"

def worker_loop():
    """Main worker loop that processes jobs until stopped"""
    while True:
        # Check if stop signal file exists
        if Path(STOP_FILE).exists():
            break
            
        try:
            job = pick_and_lock_job()
            if job:
                execute_job(job)
            else:
                # No job available, sleep briefly
                time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Worker error: {e}", file=sys.stderr)
            time.sleep(1)

if __name__ == "__main__":
    worker_loop()
