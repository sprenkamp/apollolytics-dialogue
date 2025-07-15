#!/bin/bash

# Get the full path to the Python script and root directory
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/increase.py"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/increase.log"

# Add cron job to run every 5 minutes from root directory
(crontab -l 2>/dev/null; echo "*/1 * * * * cd $ROOT_DIR && /usr/bin/python3 $SCRIPT_PATH >> $LOG_PATH 2>&1") | crontab -

echo "✅ Cron job added: increase.py will run every 1 minutes and log to increase.log" 