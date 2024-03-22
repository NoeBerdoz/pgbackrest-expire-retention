---

# PGBackRest Expire Retention Script

## Overview

This Python script utilizes basic `pgbackrest` commands (`info` and `expire`) to manage backups efficiently. The script automates the expiration of incremental and full backups according to the strategy defined by the user.

## Retention strategy

In its default configuration, the script follows the following retention strategy:
- **Incremental Backups**: Expire backups older than 7 days
- **Daily Backups**: Retain the latest backup per day for each of the last 30 days
- **Monthly Backups**: Retain the latest backup per month for each of the last 12 months
- **Yearly Backups**: Retain the latest backup per year for each of the last 20 years

The retention time for each backup type can be adapted to the user need by adding parameters to the script (see below).

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
    sudo python pgbackrest_backups_retention.py  --stanza your_stanza_name --dry-run --mode production
    ```
   _Note that the script needs the permissions to run pgbackrest commands._
   
   The parameter mode can be chosen between:
   - dev_sample_data: development mode with artifical data created with the script "pgbackrest_backups_create_database.py" 
   - dev_real_data: development with real data
   - production: production mode with real data -> if the dry mode is not activated, the backup will be definitely cleaned.
   
    The following parameters can be added to adapt the script to your needs:
    - --retention-incremental 7 (days)
    - --retention-full-daily 30 (days)
    - --retention-full-monthly 12 (months)
    - --retention-full-yearly 20 (years)

    
   **Note that with the current configuration, the script is run in dry-run mode. Once you have checked that everything works properly, you can remove the parameter --dry-run to clean the backups definitely.**

## Configuration

The script relies on the `pgbackrest` commands `info` and `expire`. Ensure that the script is executed at an appropriate frequency to achieve the desired backup retention strategy.


---
# Potential improvements
- Optimize the <365 days retentions
- What if this was all set in an Odoo module
---

Feel free to customize the content as needed for your specific project.
