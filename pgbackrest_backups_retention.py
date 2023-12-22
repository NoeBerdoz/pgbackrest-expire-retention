"""
Author: Noé Berdoz
Goal: Put in place the retention of our Pgbackrest backups
Retention :
Incremental backup every 3 hours, retention set to 1 week
Full backup once every day, retention set to one per day for the last month,
then one per month, and one per year past 365 days
"""
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

FULL = 'full'
INCREMENTAL = 'incr'

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Backup Retention Script')
parser.add_argument('--stanza', default='db-production-swiss', help='specify the PgBackRest stanza')
parser.add_argument('--log-file', default='pgbackrest_backups_retention.log', help='specify the log file path')
parser.add_argument('--dry-run', action='store_true', help='run in dry-run mode')
args = parser.parse_args()

dry_run = args.dry_run
stanza = args.stanza
log_file_path = args.log_file

command = "sudo pgbackrest info --output=json"
result = subprocess.run(command, shell=True, capture_output=True, text=True)

# converts JSON into a Python data structure
data = json.loads(result.stdout)
backups_data = data[0]['backup']

# Get current time
current_time_timestamp = int(time.time())  # Unix timestamp format
current_datetime = datetime.utcfromtimestamp(current_time_timestamp)
today_datetime = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

# Make sure to have backups sorted on their done time
sorted_backups_data = sorted(backups_data, key=lambda x: x['timestamp']['stop'])

####### LISTS #######
backups_full = []
backups_last_years = []
backups_last_months = [[] for _ in range(12)]
backups_last_weeks = []  # last weeks in the current month

####### COUNTERS #######
counter_backups_incremental = 0
counter_backups_full = 0
counter_backups_expired = 0
counter_expired_size = 0
counter_total_size = 0


# Logger function
def add_log_line(line):
    sys.stdout = open(log_file_path, 'a')
    print(line)
    sys.stdout.close()


# Execute expire commands that removes given backup
def expire_backup(backup):
    global counter_backups_expired
    global counter_expired_size

    backup_label = backup['label']
    backup_size = backup['info']['repository']['delta']

    expire_command = f"sudo pgbackrest expire --stanza={stanza} --set={backup_label} --log-level-console=detail {'--dry-run' if dry_run else ''}"
    add_log_line(f"[+] {expire_command}")
    # print(f"[-] expiring {backup_label}")
    counter_backups_expired += 1
    counter_expired_size += backup_size

    # DISABLE THIS WHILE DEV
    # Execute the expire command
    process = subprocess.Popen(expire_command, shell=True, stdout=subprocess.PIPE, text=True, bufsize=1,
                               universal_newlines=True)

    # Read and process the output line by line
    with process.stdout:
        for line in iter(process.stdout.readline, ''):
            add_log_line(line)  # Process the line as it appears

    # Wait for the subprocess to finish
    process.wait()


# Get the month index of a backup
def get_month(backup):
    if not backup:
        return

    return datetime.utcfromtimestamp(backup['timestamp']['stop']).month


# get the year index of a backup
def get_year(backup):
    if not backup:
        return

    return datetime.utcfromtimestamp(backup['timestamp']['stop']).year


# returns backups that should remain for each month
def get_monthly_backups(backups):
    # Group the data by month
    # Exemple: [list(g) for k, g in groupby('AAAABBBCCD')] --> AAAA BBB CC D
    backups_grouped_monthly = {month: list(group) for month, group in groupby(backups, key=get_month)}

    # Select the last element from each month group
    last_backup_per_months = [group[-1] for group in backups_grouped_monthly.values()]

    return last_backup_per_months


# returns backups that should remain for each year
def get_yearly_backups(backups):
    # Group the data by year
    # Exemple: [list(g) for k, g in groupby('AAAABBBCCD')] --> AAAA BBB CC D
    backup_grouped_yearly = {year: list(group) for year, group in groupby(backups, key=get_year)}

    # Select the last element from each month group
    last_backup_per_years = [group[-1] for group in backup_grouped_yearly.values()]

    # Manage the case where we remain last years backups
    last_year_monthly_backups = []
    for backup in backups:
        backup_stop_datetime = datetime.utcfromtimestamp(backup['timestamp']['stop'])  # Unix timestamp conversion

        # Check if backup concerns last 365 days
        """
        This is not optimized but we are taking in account that the script already filtered monthly the backups
        last years, if it is not the case, this will not allow the script to expire not older than one year backups.
        """
        if today_datetime - backup_stop_datetime < timedelta(days=365):
            last_year_monthly_backups.append(backup)

    return last_backup_per_years + last_year_monthly_backups


add_log_line('------------------------')
add_log_line(f"Launching script on: {current_datetime}")
for backup in sorted_backups_data:
    backup_type = backup['type']
    backup_size = backup['info']['repository']['delta']
    backup_stop_datetime = datetime.utcfromtimestamp(backup['timestamp']['stop'])  # Unix timestamp conversion
    backup_label = backup['label']

    # increment total size counter
    counter_total_size += backup_size

    # increment incremental backups counter
    if backup_type == INCREMENTAL:
        counter_backups_incremental += 1

    is_within_last_week = today_datetime - backup_stop_datetime < timedelta(weeks=1)

    # clean expired incremental backups
    if not is_within_last_week and backup_type == INCREMENTAL:
        expire_backup(backup)

    # Filters full backups
    if backup_type == FULL:
        counter_backups_full += 1

        backups_full.append(backup)

        # Check if backup concerns last years
        if today_datetime.year > backup_stop_datetime.year:
            backups_last_years.append(backup)

        # Check if backup concerns last months
        if today_datetime.month > backup_stop_datetime.month and today_datetime.year == backup_stop_datetime.year:
            backups_last_months.append(backup)

        # Check if backup concerns last weeks
        if today_datetime - backup_stop_datetime < timedelta(days=31):
            backups_last_weeks.append(backup)

backups_monthly_remaining = get_monthly_backups(backups_last_months)
backups_yearly_remaining = get_yearly_backups(backups_last_years)

# Clean expired full backups
for backup in backups_full:
    if backup not in backups_monthly_remaining and backup not in backups_yearly_remaining and backup not in backups_last_weeks:
        expire_backup(backup)

add_log_line("-------- Resume --------")
add_log_line(f"Number of full backups: {counter_backups_full}")
add_log_line(f"Number of incremental backups: {counter_backups_incremental}")
add_log_line(f"Number of expired backups cleaned: {counter_backups_expired}")
add_log_line(f"Size of expired: {humanize.naturalsize(counter_expired_size)}")
add_log_line(f"Total size: {humanize.naturalsize(counter_total_size)}")
add_log_line(f"remaining size: {humanize.naturalsize(counter_total_size - counter_expired_size)}")
