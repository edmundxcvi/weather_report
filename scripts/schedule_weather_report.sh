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
CRON_CMD="$ROOT_DIR/scripts/invoke_weather_report.sh"
CRON_JOB="*/$INTERVAL * * * * $CRON_CMD"

# Ensure that job is executable
chmod +x $ROOT_DIR/scripts/invoke_weather_report.sh

# Copy existing cronjobs to variable (excluding errors, which are sent to /dev/null)
CRONTAB=$(crontab -l 2>/dev/null )

# Use grep to filter out any lines which match the job text
# (-F means match strings (instead of default regex matching))
# (-v inverts selection to select *non*-matching rows)
# Make sure to echo the variable in quotes to avoid expanding the asterisks
# i.e. `echo "$VAR"` not `echo $VAR`
NEW_CRONTAB=$(echo "$CRONTAB" | grep -vF $CRON_CMD)

# Add new cronjob to end of crontab
NEW_CRONTAB=$({
    echo "$NEW_CRONTAB"
    echo "$CRON_JOB"
})

# Pipe output to crontab
# (-e interprets escaped characters so \n is a new line, not the characters \n)
echo "$NEW_CRONTAB" | crontab -

# Check the exit code of the above statement
if [ $? -ne 0 ]; then
    echo "Error: Failed to update the crontab."
    exit 1
fi

# Report
echo "Cron job $CRON_JOB created successfully"
