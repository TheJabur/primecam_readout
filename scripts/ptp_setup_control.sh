#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit
fi

# Detect primary interface (excluding loopback and wireless)
INTERFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -vE 'lo|wlan|virbr' | head -n 1)

echo "--- Initializing PTP Grandmaster Setup ---"
echo "Detected Interface: $INTERFACE"

# 1. Install Dependencies
apt update && apt install -y linuxptp

# 2. Configure ptp4l as Grandmaster
echo "Configuring ptp4l..."
mkdir -p /etc/linuxptp
cat <<EOF > /etc/linuxptp/ptp4l.conf
[global]
priority1               0
priority2               0
domainNumber            0
network_transport       L2
delay_mechanism         E2E
transportSpecific       0x0
write_phase_mode        0

[$INTERFACE]
EOF

# 3. Restart and Enable Service
echo "Restarting ptp4l service..."
systemctl stop ptp4l 2>/dev/null
systemctl enable ptp4l
systemctl restart ptp4l

echo "--- Master Setup Complete ---"
echo "Interface used: $INTERFACE"
echo "Check status:   sudo pmc -u -b 0 'GET TIME_STATUS_NP'"
echo "Monitor logs:   journalctl -u ptp4l -f"