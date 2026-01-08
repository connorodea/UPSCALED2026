#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(pwd)}"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required. Install Node 18+ first." >&2
  exit 1
fi

cd "$REPO_DIR"

npm install
npm run build

echo "Local setup complete."
echo "- Start CLI: npm start"
echo "- Start web: npm run web:dev"
echo "- Start print agent: npm run print:dev"
