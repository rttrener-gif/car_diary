#!/usr/bin/env bash
# One-command update script for Car Diary Bot
set -euo pipefail

echo "==> Pulling latest changes..."
git pull

echo "==> Restarting service..."
systemctl restart car_diary_bot

echo "==> Done. Status:"
systemctl status car_diary_bot --no-pager
