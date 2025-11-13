#!/usr/bin/env python3
import click
import multiprocessing
import signal
import sys
import time
import subprocess
from pathlib import Path
from db import init_db, get_conn
from models import Job
from utils import get_config, set_config
from datetime import datetime, timezone

PID_FILE = "queuectl.pid"
STOP_FILE = "queuectl.stop"

def start_workers_daemon(count):
    import os
    import subprocess
    
    if Path(PID_FILE).exists():
        click.echo("Workers may already be running. Use 'stop' first.")
        return
    
    if Path(STOP_FILE).exists():
        Path(STOP_FILE).unlink()
    
    init_db()
    pids = []
    script_dir = Path(__file__).parent
    worker_script = script_dir / "worker_runner.py"
    
    for i in range(count):
        log_file = open(f'worker_{i}.log', 'w')
        proc = subprocess.Popen(
            [sys.executable, str(worker_script)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )
        pids.append(str(proc.pid))
        time.sleep(0.1)
    
    with open(PID_FILE, 'w') as f:
        f.write('\n'.join(pids))
    
    click.echo(f"✓ Started {count} worker(s) with PIDs: {', '.join(pids)}")
    click.echo(f"  Logs: worker_0.log, worker_1.log, ...")

def stop_workers_daemon():
    if not Path(PID_FILE).exists():
        click.echo("No workers running.")
        return
    
    Path(STOP_FILE).touch()
    
    with open(PID_FILE, 'r') as f:
        pids = [int(line.strip()) for line in f if line.strip()]
    
    click.echo("Sending stop signal to workers...")
    time.sleep(3)
    
    stopped = 0
    import os
    for pid in pids:
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGTERM)
            stopped += 1
            time.sleep(0.5)
        except ProcessLookupError:
            stopped += 1
        except Exception as e:
            click.echo(f"Error stopping PID {pid}: {e}")
    
    Path(PID_FILE).unlink()
    if Path(STOP_FILE).exists():
        Path(STOP_FILE).unlink()
    
    click.echo(f"✓ Stopped {stopped} worker(s).")

def get_active_workers():
    if not Path(PID_FILE).exists():
        return 0
    
    try:
        with open(PID_FILE, 'r') as f:
            pids = [int(line.strip()) for line in f if line.strip()]
        
        alive = 0
        for pid in pids:
            try:
                import os
                os.kill(pid, 0)
                alive += 1
            except ProcessLookupError:
                pass
        
        return alive
    except Exception:
        return 0

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)

@click.group()
def cli():
    init_db()

@cli.command()
@click.argument('job_json')
def enqueue(job_json):
    try:
        job = Job.from_json(job_json)
        job.save()
        click.echo(f"✓ Job {job.id} enqueued successfully.")
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--count', default=1, help='Number of worker processes to start')
def start(count):
    if count < 1:
        click.echo("Error: count must be at least 1", err=True)
        sys.exit(1)
    
    start_workers_daemon(count)

@cli.command()
def stop():
    stop_workers_daemon()

@cli.command()
def status():
    conn = get_conn()
    rows = conn.execute(
        "SELECT state, COUNT(*) as count FROM jobs GROUP BY state"
    ).fetchall()
    counts = {row['state']: row['count'] for row in rows}
    conn.close()
    
    click.echo("Job Queue Status:")
    click.echo("─" * 40)
    for state in ['pending', 'processing', 'completed', 'failed', 'dead']:
        count = counts.get(state, 0)
        click.echo(f"  {state.capitalize():12} : {count}")
    
    click.echo("─" * 40)
    active = get_active_workers()
    click.echo(f"  Active Workers: {active}")

@cli.command()
def dlq_list():
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, command, attempts, output, created_at 
        FROM jobs 
        WHERE state='dead'
        ORDER BY updated_at DESC
    """).fetchall()
    conn.close()
    
    if not rows:
        click.echo("Dead Letter Queue is empty.")
        return
    
    click.echo(f"Dead Letter Queue ({len(rows)} jobs):")
    click.echo("─" * 80)
    
    for r in rows:
        cmd_preview = r['command'][:50] + ('...' if len(r['command']) > 50 else '')
        click.echo(f"ID: {r['id']}")
        click.echo(f"  Command: {cmd_preview}")
        click.echo(f"  Attempts: {r['attempts']}")
        click.echo(f"  Created: {r['created_at']}")
        if r['output']:
            output_preview = r['output'][:100]
            click.echo(f"  Output: {output_preview}")
        click.echo()

@cli.command()
@click.argument('job_id')
def retry(job_id):
    conn = get_conn()
    job = conn.execute(
        "SELECT state FROM jobs WHERE id=?", 
        (job_id,)
    ).fetchone()
    
    if not job:
        conn.close()
        click.echo(f"✗ Job {job_id} not found.", err=True)
        sys.exit(1)
    
    if job['state'] != 'dead':
        conn.close()
        click.echo(f"✗ Job {job_id} is not in DLQ (current state: {job['state']})", err=True)
        sys.exit(1)
    
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        UPDATE jobs 
        SET state='pending', attempts=0, next_retry_at=NULL, output=NULL, updated_at=?
        WHERE id=?
    """, (now, job_id))
    conn.commit()
    conn.close()
    
    click.echo(f"✓ Job {job_id} moved back to queue.")

@cli.command()
@click.option('--key', required=True, help='Configuration key')
@click.option('--value', required=True, help='Configuration value')
def config_set(key, value):
    set_config(key, value)
    click.echo(f"✓ Config '{key}' set to '{value}'")

@cli.command()
@click.option('--key', required=True, help='Configuration key')
def config_get(key):
    value = get_config(key)
    if value:
        click.echo(f"{key} = {value}")
    else:
        click.echo(f"Config key '{key}' not found.", err=True)

if __name__ == "__main__":
    cli()
