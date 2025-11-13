#!/bin/bash

echo "QueueCTL Integration Test"
echo "=========================="
echo

# Cleanup
echo "Step 1: Cleanup"
rm -f ../queue.db ../queue.db-shm ../queue.db-wal ../queuectl.pid ../queuectl.stop ../worker_*.log
cd ..
python3 queuectl.py stop 2>/dev/null || true
sleep 1
echo "Done"
echo

# Enqueue jobs
echo "Step 2: Enqueue test jobs"
python3 queuectl.py enqueue '{"id":"job1","command":"echo test1"}'
python3 queuectl.py enqueue '{"id":"job2","command":"false"}'
python3 queuectl.py enqueue '{"id":"job3","command":"sleep 2 && echo test2"}'
python3 queuectl.py enqueue '{"id":"job4","command":"echo test3"}'
echo

# Start workers
echo "Step 3: Start workers"
python3 queuectl.py start --count 2
sleep 2
echo

# Initial status
echo "Step 4: Check status"
python3 queuectl.py status
echo

# Wait for processing
echo "Step 5: Wait for jobs to process"
sleep 8
python3 queuectl.py status
echo

# Check DLQ
echo "Step 6: Check Dead Letter Queue"
python3 queuectl.py dlq-list
echo

# Retry failed job
echo "Step 7: Retry failed job"
FAILED_JOB=$(python3 -c "
import sqlite3
conn = sqlite3.connect('queue.db')
row = conn.execute('SELECT id FROM jobs WHERE state=\"dead\" LIMIT 1').fetchone()
conn.close()
print(row[0] if row else 'none')
")

if [ "$FAILED_JOB" != "none" ]; then
    python3 queuectl.py retry $FAILED_JOB
    sleep 6
    python3 queuectl.py status
    echo
fi

# Final status
echo "Step 8: Final status"
python3 queuectl.py status
echo

echo "Step 9: Final DLQ"
python3 queuectl.py dlq-list
echo

# Stop workers
echo "Step 10: Stop workers"
python3 queuectl.py stop
echo

echo "Test complete"
