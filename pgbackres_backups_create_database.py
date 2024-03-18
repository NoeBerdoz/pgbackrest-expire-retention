"""
Author: Aurélien Clerc
Goal: Generate a list imitating pgbackrest backups to test the script pgbackrest_backups_retention.py
The script generates 7 incremental backups a day (00:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00) and 1 full backup
a day (03:00) between a start and an end date.
"""

# Imports
try:
    import json
    import sys
    from datetime import datetime, timedelta
    import subprocess
    import time
    import argparse
    import humanize
    from itertools import groupby
except ImportError as error:
    print(f"Error: {error}")
    print("Please install the required packages before running this script.")
    print("You can install them using:")
    print("pip install json sys humanize")
    sys.exit(1)

# Initialise the backups list
backup = []

# Start date for generating backups
start_date = datetime(2021, 1, 1)

# End date for generating backups
end_date = datetime(2024, 1, 30, 11, 00)

# Backup generation
current_date = start_date
while current_date <= end_date:
    # Generating "full" backups at 03:00
    if current_date.hour == 3:
        data_type = "full"
    # Generating "incr" backups
    else:
        data_type = "incr"

    data = {
        "label": current_date.strftime("%Y%m%d%H%M%S") + "-003004" + data_type[0].upper(),  # Label format: YYYYMMDDHHMMSS-003004I or -003004F
        "timestamp": {
            "start": 0,
            "stop": int(current_date.timestamp())
        },
        "type": data_type
    }
    backup.append(data)

    # Move to the next 3-hour interval
    current_date += timedelta(hours=3)
print(backup[-10:])

# Writing datasets to a JSON file
with open("backups.json", "w") as f:
    json.dump(backup, f, indent=4)