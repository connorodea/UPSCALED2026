#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/upscaled/Upscaled_inv_processing}"
ENV_FILE="${ENV_FILE:-/etc/upscaled/inventory.env}"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required. Install Node 18+ first." >&2
  exit 1
fi

mkdir -p /etc/upscaled

if [ ! -f "$ENV_FILE" ]; then
  cp "$REPO_DIR/deploy/env.example" "$ENV_FILE"
  echo "Created env file at $ENV_FILE. Please edit it with real values." >&2
fi

cd "$REPO_DIR"

npm install
npm run build
chmod +x "$REPO_DIR/deploy/nightly_hub_backup.sh"

cp "$REPO_DIR/deploy/systemd/upscaled-web.service" /etc/systemd/system/upscaled-web.service
cp "$REPO_DIR/deploy/systemd/upscaled-nightly.service" /etc/systemd/system/upscaled-nightly.service
cp "$REPO_DIR/deploy/systemd/upscaled-nightly.timer" /etc/systemd/system/upscaled-nightly.timer

systemctl daemon-reload
systemctl enable upscaled-web.service
systemctl restart upscaled-web.service
systemctl enable upscaled-nightly.timer
systemctl start upscaled-nightly.timer

echo "Install complete. Configure nginx using deploy/nginx/inventory.upscaledinc.com.conf"
