#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/ui/downloads"
PACKAGE_DIR="$ROOT_DIR/deploy/print_agent/macos/package"

cd "$ROOT_DIR"

npm install

npx esbuild src/printAgent.ts --bundle --platform=node --outfile=dist/printAgent.bundle.js

TARGET_ARCH="${PRINT_AGENT_ARCH:-arm64}"
npx pkg dist/printAgent.bundle.js \
  --targets "node18-macos-${TARGET_ARCH}" \
  --output dist/upscaled-print-agent

mkdir -p "$PACKAGE_DIR/usr/local/bin"
cp dist/upscaled-print-agent "$PACKAGE_DIR/usr/local/bin/upscaled-print-agent"

mkdir -p "$PACKAGE_DIR/Library/LaunchAgents"
cp "$ROOT_DIR/deploy/print_agent/macos/com.upscaled.printagent.plist" \
  "$PACKAGE_DIR/Library/LaunchAgents/com.upscaled.printagent.plist"

pkgbuild \
  --root "$PACKAGE_DIR" \
  --identifier com.upscaled.printagent \
  --version 1.0.0 \
  --install-location / \
  "$OUTPUT_DIR/upscaled-print-agent-macos.pkg"

echo "Built $OUTPUT_DIR/upscaled-print-agent-macos.pkg"
