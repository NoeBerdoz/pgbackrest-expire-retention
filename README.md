---

# PGBackRest Expire Retention Script

## Overview

This Python script utilizes basic `pgbackrest` commands (`info` and `expire`) to manage backups efficiently. When executed at the appropriate time, the script automates the expiration of incremental backups that are more than a week old. It also retains the oldest backup per month from the last several months and follows a similar approach for the last years, preserving the oldest backup per year.

## Usage

To use the script, follow these steps:

1. Ensure that `pgbackrest` is properly installed and configured on your system.

2. Clone the repository:

    ```bash
    git clone https://github.com/your-username/pgbackrest-expire-retention.git
    ```

3. Navigate to the project directory:

    ```bash
    cd pgbackrest-expire-retention
    ```

4. Run the script:

    ```bash
    sudo python pgbackrest_backups_retention.py
    ```
   _Note that the script needs the permissions to run pgbackrest commands._

   **The script is currently with the --dry-run option set, so you can see what would happens in the logs, if you want to exit the dry run, edit `expire_command` variable**

## Configuration

The script relies on the `pgbackrest` commands `info` and `expire`. Ensure that the script is executed at an appropriate frequency to achieve the desired backup retention strategy.

## Retention Policy

The script follows the following retention policy:

- **Incremental Backups:** Expire backups older than 1 week.
- **Monthly Backups:** Retain the oldest backup per month from the last 12 months.
- **Yearly Backups:** Retain the oldest backup per year.

When entering a new year, the retention will stick to the monthly approach for the last 365 days.

---
# Potential improvements
- Optimize the <365 days retentions
- Make the retention strategy configurable
- What if this was all set in an Odoo module
---

Feel free to customize the content as needed for your specific project.
