"""
Author: Noé Berdoz, Aurélien Clerc
Goal: Put in place the retention of our Pgbackrest backups
Retention :
Incremental backup every 3 hours, retention set to 1 week
Full backup once every day, retention set to one per day for the last month,
then one per month, and one per year past 365 days
"""

# Necessary imports
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

# Retention parameters definition
incr_backups_retention_time = 7 #days
full_daily_backup_retention_time = 30 #days
full_monthly_backup_retention_time = 12 #months
full_yearly_backup_retention_time = 20 #years

FULL = 'full'
INCREMENTAL = 'incr'

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Backup Retention Script')
parser.add_argument('--stanza', default='db-production-swiss', help='specify the PgBackRest stanza')
parser.add_argument('--log-file', default='pgbackrest_backups_retention.log', help='specify the log file path')
parser.add_argument('--dry-run', action='store_true', help='run in dry-run mode')
parser.add_argument('--mode', default='dev_real_database', help='Specify the mode: dev_sample_data, dev_real_data, production')
args = parser.parse_args()

dry_run = args.dry_run
stanza = args.stanza
log_file_path = args.log_file
mode = args.mode

# possible value for --mode : dev_sample_data, dev_real_data, production

# In dev mode ?
DEV = False
if mode == 'dev_real_data' or mode =='dev_sample_data':
    DEV = True

# Import the backup from the real data with pgbackrest
if mode == 'dev_real_data' or mode == 'production':
    command = "pgbackrest info --output=json"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # converts JSON into a Python data structure
    data = json.loads(result.stdout)
    backups_data = data[0]['backup']

# Import the backups from sample data
if mode == 'dev_sample_data':
    # Import the backups from JSON file (for test purposes)
    with open('backups.json', "r") as file:
        # Load the JSON data from the file
        data = json.load(file)
    backups_data = data

# Make sure to have backups sorted on their done time
sorted_backups_data = sorted(backups_data, key=lambda x: x['timestamp']['stop'])

# Get current time
current_time_timestamp = int(time.time())  # Unix timestamp format
current_datetime = datetime.utcfromtimestamp(current_time_timestamp)
today_datetime = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

# Set current time (for test purposes)
# current_datetime = datetime(2024, 1, 1, 15, 30)
# current_time_timestamp = int(current_datetime.timestamp())
# today_datetime = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)

####### LISTS #######
backups_to_keep = [] #List that store all the backup we want to keep

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
    if DEV:
        backup_size = 0
    else:
        backup_size = backup['info']['repository']['delta']

    expire_command = f"sudo pgbackrest expire --stanza={stanza} --set={backup_label} --log-level-console=detail {'--dry-run' if dry_run else ''}"
    if DEV:
        print(f"(Dev mode) [+] {expire_command}")
    else:
        add_log_line(f"[+] {expire_command}")
    counter_backups_expired += 1
    counter_expired_size += backup_size

    if mode == 'production':
        # Execute the expire command
        process = subprocess.Popen(expire_command, shell=True, stdout=subprocess.PIPE, text=True, bufsize=1,
                                   universal_newlines=True)

        # Read and process the output line by line
        with process.stdout:
            for line in iter(process.stdout.readline, ''):
                add_log_line(line)  # Process the line as it appears

        # Wait for the subprocess to finish
        process.wait()

# Function to get the backup day
def get_day(backup):
    if not backup:
        return

    return datetime.utcfromtimestamp(backup['timestamp']['stop']).day

# Function to get the backup month
def get_month(backup):
    if not backup:
        return

    return datetime.utcfromtimestamp(backup['timestamp']['stop']).month

# Function to get the backup year
def get_year(backup):
    if not backup:
        return

    return datetime.utcfromtimestamp(backup['timestamp']['stop']).year


### Select the incremental and daily full backups to keep ###
for backup in sorted_backups_data:
    # Keep incremental backups less xxx days old (as defined above):
    if backup["type"] == 'incr' and backup['timestamp']["stop"] > current_time_timestamp - timedelta(days=incr_backups_retention_time).total_seconds():
        backups_to_keep.append(backup)

    # Keep full backups less than xxx months old (as defined above):
    if backup["type"] == 'full' and backup['timestamp']["stop"] > current_time_timestamp - timedelta(days=full_daily_backup_retention_time).total_seconds():
        backups_to_keep.append(backup)

### Select the monthly backups to keep ###

# Retention time conversion from months to years + months (e.g.: 15 months = 1 year + 3 months)
year_diff = full_monthly_backup_retention_time // 12
month_diff = full_monthly_backup_retention_time % 12
# Start month of the monthly backup retention time
month = current_datetime.month - month_diff
year = current_datetime.year - year_diff
if month < 1:
    month+=12
    year-=1

# Loop over all the months where the monthly backups have to be retained. Keep the last full backup of each of these
# months
for i in range(full_monthly_backup_retention_time):
    all_full_backup_of_the_month = []
    for backup in sorted_backups_data:
        if backup["type"] == 'full' and get_month(backup) == month and get_year(backup) == year:
            all_full_backup_of_the_month.append(backup)

    if not all_full_backup_of_the_month:
        print(f'No backups for {month} {year}')
    elif all_full_backup_of_the_month[-1] not in backups_to_keep:
        backups_to_keep.append(all_full_backup_of_the_month[-1])

    # to the next month
    if month != 12:
        month +=1
    else:
        year +=1
        month = 1

### Select the yearly backups to keep ###
year = get_year(sorted_backups_data[0])
start_year = current_datetime.year - full_yearly_backup_retention_time
# Loop over all the years where the yearly backups have to be retained. Keep the last full backup of each of these
# years
for year in range(start_year, current_datetime.year+1):
    all_full_backup_of_the_year = []
    for backup in sorted_backups_data:
        if backup["type"] == 'full' and get_year(backup) == year:
            all_full_backup_of_the_year.append(backup)

    if not all_full_backup_of_the_year:
        print(f'No backups for {year}')
        # add_log_line(f'No backups for {year}')
    elif all_full_backup_of_the_year[-1] not in backups_to_keep:
        backups_to_keep.append(all_full_backup_of_the_year[-1])

sorted_backups_to_keep = sorted(backups_to_keep, key=lambda x: x['timestamp']['stop'])

if DEV:
    for backup in sorted_backups_to_keep:
        print(f"Backup {backup['label'][0:8]} of type {backup['type']} is kept")
        print('----')

if DEV:
    print('------------------------')
    print(f"Launching script on: {current_datetime}")
else:
    add_log_line('------------------------')
    add_log_line(f"Launching script on: {current_datetime} (mode={mode})")


# Clean expired full backups
for backup in sorted_backups_data:
    backup_type = backup['type']
    if mode == 'dev_real_data' or mode == 'production':
        backup_size = backup['info']['repository']['delta']
    else:
        backup_size = 0
    backup_stop_datetime = datetime.utcfromtimestamp(backup['timestamp']['stop'])  # Unix timestamp conversion
    backup_label = backup['label']

    #increment total size counter
    counter_total_size += backup_size

    if backup_type == INCREMENTAL:
        counter_backups_incremental += 1
    elif backup_type == FULL:
        counter_backups_full += 1

    if backup not in backups_to_keep:
        expire_backup(backup)

if mode == ('dev_sample_data'):
    print("-------- Resume --------")
    print(f"Number of full backups: {counter_backups_full}")
    print(f"Number of incremental backups: {counter_backups_incremental}")
    print(f"Number of expired backups cleaned: {counter_backups_expired}")
    print(f"Size of expired: {humanize.naturalsize(counter_expired_size)} (=0 because backups in sample data have no size)")
    print(f"Total size: {humanize.naturalsize(counter_total_size)} (=0 because backups in sample data have no size)")
    print(f"remaining size: {humanize.naturalsize(counter_total_size - counter_expired_size)} (=0 because backups in sample data have no size)")
elif mode == 'dev_real_data':
    print("-------- Resume --------")
    print(f"Number of full backups: {counter_backups_full}")
    print(f"Number of incremental backups: {counter_backups_incremental}")
    print(f"Number of expired backups cleaned: {counter_backups_expired}")
    print(f"Size of expired: {humanize.naturalsize(counter_expired_size)}")
    print(f"Total size: {humanize.naturalsize(counter_total_size)}")
    print(f"remaining size: {humanize.naturalsize(counter_total_size - counter_expired_size)}")
else:
    add_log_line("-------- Resume --------")
    add_log_line(f"Number of full backups: {counter_backups_full}")
    add_log_line(f"Number of incremental backups: {counter_backups_incremental}")
    add_log_line(f"Number of expired backups cleaned: {counter_backups_expired}")
    add_log_line(f"Size of expired: {humanize.naturalsize(counter_expired_size)}")
    add_log_line(f"Total size: {humanize.naturalsize(counter_total_size)}")
    add_log_line(f"remaining size: {humanize.naturalsize(counter_total_size - counter_expired_size)}")