#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

echo "--- Initializing Persistent PTP Slave Setup for ZCU111 ---"

# 1. Path Discovery
PTP4L_PATH=$(which ptp4l)
PHC2SYS_PATH=$(which phc2sys)
PMC_PATH=$(which pmc)
IFCONFIG_PATH=$(which ifconfig)

# 2. Disable Conflicting Services
echo "Disabling standard time services..."
timedatectl set-ntp false
systemctl stop systemd-timesyncd 2>/dev/null
systemctl mask systemd-timesyncd 2>/dev/null
killall -9 ptp4l phc2sys 2>/dev/null

# 3. Create ptp4l Configuration
echo "Writing /etc/linuxptp/ptp4l.conf..."
mkdir -p /etc/linuxptp
cat <<EOF > /etc/linuxptp/ptp4l.conf
[global]
priority1               255
priority2               255
domainNumber            0
network_transport       L2
delay_mechanism         E2E
transportSpecific       0x0
clientOnly              1
fault_reset_interval    4

[eth0]
EOF

# 4. Create ptp4l Systemd Service
echo "Creating ptp4l.service..."
cat <<EOF > /etc/systemd/system/ptp4l.service
[Unit]
Description=PTP Slave for ZCU111
After=network.target

[Service]
Type=simple
# Ensure eth0 is up so the PHC device is exported to the kernel
ExecStartPre=$IFCONFIG_PATH eth0 up
ExecStart=$PTP4L_PATH -f /etc/linuxptp/ptp4l.conf -i eth0
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 5. Create phc2sys Systemd Service
echo "Creating phc2sys.service..."
cat <<EOF > /etc/systemd/system/phc2sys.service
[Unit]
Description=Synchronize system clock to PHC
After=ptp4l.service
Wants=ptp4l.service

[Service]
Type=simple
# Initialize Grandmaster settings and 37s UTC offset
ExecStartPre=$PMC_PATH -u -b 0 -t 1 "SET GRANDMASTER_SETTINGS_NP clockClass 248 clockAccuracy 0xfe offsetScaledLogVariance 0xffff currentUtcOffset 37 leap61 0 leap59 0 currentUtcOffsetValid 1 ptpTimescale 1 timeTraceable 1 frequencyTraceable 0 timeSource 0xa0"
# Run sync with explicit offset to avoid 'Waiting for ptp4l' hang
ExecStart=/usr/local/sbin/phc2sys -s eth0 -c CLOCK_REALTIME --step_threshold=1 --transportSpecific=1 -z /var/run/ptp4l -O 37 -F 0
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=0

[Install]
WantedBy=multi-user.target
EOF

# 6. Finalize
echo "Reloading systemd and starting services..."
systemctl daemon-reload
systemctl enable ptp4l phc2sys
systemctl restart ptp4l
sleep 2
systemctl restart phc2sys

echo "--- Setup Complete ---"
echo "Verify hardware sync: journalctl -u ptp4l -f"
echo "Verify system sync:   journalctl -u phc2sys -f"