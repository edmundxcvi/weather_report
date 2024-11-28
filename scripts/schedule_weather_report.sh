#!/bin/bash

# Parse argument
# Ensure single argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <interval_in_minutes>"
    exit 1
fi

# Ensure argument is positive integer
INTERVAL="$1"
if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]] || [ "$INTERVAL" -le 0 ]; then
    echo "Error: Interval must be a positive integer."
    exit 1
fi

# Create job
ROOT_DIR="$(readlink -f $(dirname $(dirname "$BASH_SOURCE[0]}")))"
CRON_JOB="*/$INTERVAL * * * * $ROOT_DIR/scripts/invoke_weather_report.sh"

# Copy existing cronjobs to variable (excluding errors, which are sent to /dev/null)
# and use grep to filter out any lines which match the job text
# (-F means match strings (instead of default regex matching))
# (-v inverts selection to select *non*-matching rows)
CRONTAB=$(crontab -l 2>/dev/null | grep -vF $CRON_JOB)

# Add new cronjob to end of crontab
NEW_CRONTAB=$(echo -e "$CRONTAB\n$CRON_JOB")

# Pipe output to crontab
# (-e interprets escaped characters so \n is a new line, not the characters \n)
echo -e NEW_CRONTAB | crontab -

# Report
echo "Cron job $CRON_JOB created successfully"
