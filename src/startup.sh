#!/bin/bash
# This is the startup script for CCATpHive.

# The CCATpHive directory
SCRIPTS_DIR="/path/to/CCATpHive/"


# Add as a cron job on startup:
# 1. Make this script executable: 'chmod +x startup.sh'.
# 2. Open cron table: 'crontab -e'.
# 3. Add this line: '@reboot /path/to/startup.sh'.
# 4. Save and quit cron.
# 5. Verify: 'crontab -l'.


# Step 1: Run the initialization script
sudo python3 "$SCRIPTS_DIR/init_multi.py"

# Step 2: Startup the drones
# Should we start all drones or do a check?
# How do we stop these processes? Or do we want to?
python3 "$SCRIPTS_DIR/drone.py" 1 &
python3 "$SCRIPTS_DIR/drone.py" 2 &
python3 "$SCRIPTS_DIR/drone.py" 3 &
python3 "$SCRIPTS_DIR/drone.py" 4 &