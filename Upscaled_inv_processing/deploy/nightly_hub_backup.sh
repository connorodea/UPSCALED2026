#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/opt/upscaled/Upscaled_inv_processing"
SCRAPER_VENV="$ROOT_DIR/08_AUTOMATION/CLI_Tools/auction_scraper/.venv"
cd "$ROOT_DIR"

if [ -x "$SCRAPER_VENV/bin/python" ]; then
  "$SCRAPER_VENV/bin/python" 08_AUTOMATION/CLI_Tools/auction_scraper/build_master_manifest.py
else
  python3 08_AUTOMATION/CLI_Tools/auction_scraper/build_master_manifest.py
fi

BACKUP_DIR="01_SOURCING/Backups/$(date +%F)"
mkdir -p "$BACKUP_DIR"

cp -a Upscaled_inv_processing/data "$BACKUP_DIR/data"
cp -a 01_SOURCING/Inventory_Hub "$BACKUP_DIR/Inventory_Hub"
cp -a 01_SOURCING/Auctions/master_manifest "$BACKUP_DIR/master_manifest"

ARCHIVE_NAME="01_SOURCING/Backups/inventory_backup_$(date +%F).tar.gz"
tar -czf "$ARCHIVE_NAME" -C "01_SOURCING/Backups" "$(date +%F)"
