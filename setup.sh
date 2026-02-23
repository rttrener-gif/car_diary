#!/usr/bin/env bash
# First-time setup script for Debian 11 (clean server)
set -euo pipefail

INSTALL_DIR="/root/car_diary_bot"
SERVICE_FILE="/etc/systemd/system/car_diary_bot.service"

echo "==> Updating package list and installing dependencies..."
apt-get update -y
apt-get install -y python3 python3-pip git

echo "==> Installing Python packages..."
pip3 install -r "$INSTALL_DIR/requirements.txt"

echo "==> Copying systemd service file..."
cp "$INSTALL_DIR/car_diary_bot.service" "$SERVICE_FILE"

echo "==> Reloading systemd..."
systemctl daemon-reload

echo "==> Enabling and starting service..."
systemctl enable car_diary_bot
systemctl start car_diary_bot

echo ""
echo "==> Setup complete! Check status with:"
echo "    systemctl status car_diary_bot"
echo ""
echo "IMPORTANT: Make sure /root/car_diary_bot/.env is properly configured!"
