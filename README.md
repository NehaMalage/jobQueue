# QueueCTL - Background Job Queue System

A CLI-based job queue system with worker processes, exponential backoff retries, and Dead Letter Queue support.

## Features

- Job queue management with persistent storage
- Multiple worker processes for parallel execution
- Automatic retry with exponential backoff
- Dead Letter Queue for permanently failed jobs
- Simple CLI interface

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start Workers
```bash
python3 queuectl.py start --count 2
```

### Enqueue Jobs
```bash
# Basic job
python3 queuectl.py enqueue '{"command":"echo Hello"}'

# Job with custom retries
python3 queuectl.py enqueue '{"command":"python script.py","max_retries":5}'

# Job with specific ID
python3 queuectl.py enqueue '{"id":"job-123","command":"ls -la"}'
```

### Check Status
```bash
python3 queuectl.py status
```

### Dead Letter Queue
```bash
# List failed jobs
python3 queuectl.py dlq-list

# Retry a failed job
python3 queuectl.py retry <job-id>
```

### Configuration
```bash
# Get config
python3 queuectl.py config-get --key max_retries

# Set config
python3 queuectl.py config-set --key max_retries --value 5
```

### Stop Workers
```bash
python3 queuectl.py stop
```

## Job Lifecycle

```
pending → processing → completed
   ↓           ↓
   ↓        failed → (retry with backoff)
   ↓           ↓
   └─────→  dead (DLQ)
```

## Retry Logic

Jobs are retried with exponential backoff:
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Attempt 4: Wait 8 seconds

After max retries, jobs move to Dead Letter Queue.

## Testing

```bash
cd tests
chmod +x test_flow.sh
./test_flow.sh
```

## Project Structure

```
queuectl/
├── queuectl.py          # CLI interface
├── db.py                # Database operations
├── models.py            # Job model
├── worker.py            # Job execution logic
├── worker_runner.py     # Worker process
├── utils.py             # Utilities
├── requirements.txt     # Dependencies
├── README.md            # Documentation
└── tests/
    └── test_flow.sh     # Integration tests
```

## Configuration

Default configuration:
- `max_retries`: 3
- `backoff_base`: 2

## Database Schema

**Jobs Table:**
- `id`: Job identifier
- `command`: Shell command to execute
- `state`: Job state (pending/processing/completed/failed/dead)
- `attempts`: Number of execution attempts
- `max_retries`: Maximum retry attempts
- `next_retry_at`: Next retry timestamp
- `output`: Command output
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Requirements

- Python 3.7+
- SQLite3
- click

## License

MIT
