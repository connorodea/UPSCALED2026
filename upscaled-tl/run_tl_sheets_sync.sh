#!/bin/zsh
set -euo pipefail

ROOT="/Users/connorodea/Library/Mobile Documents/com~apple~CloudDocs/UPSCALED2026"
PYTHON="${ROOT}/upscaled-tl/.venv/bin/python"
CREDS_FILE="${ROOT}/upscaled-tl/config/techliquidators.env"
STORAGE_STATE="${HOME}/.config/upscaled-tl/session/storage_state.json"

if [[ -f "${CREDS_FILE}" ]]; then
  set -a
  source "${CREDS_FILE}"
  set +a
fi

if [[ "${TL_AUTOMATE_LOGIN:-0}" == "1" && -n "${TL_USERNAME:-}" && -n "${TL_PASSWORD:-}" ]]; then
  "${PYTHON}" "${ROOT}/08_AUTOMATION/CLI_Tools/auction_scraper/get_techliquidators_cookies.py" \
    --browser chromium --creds-file "${CREDS_FILE}" || true
else
  echo "Skipping cookie refresh (set TL_AUTOMATE_LOGIN=1 to auto-login)." >&2
fi
"${PYTHON}" "${ROOT}/08_AUTOMATION/CLI_Tools/auction_scraper/sync_techliquidators_orders.py" \
  --cookie-file "${ROOT}/upscaled-tl/data/techliquidators/techliquidators_cookies.txt"
"${PYTHON}" "${ROOT}/upscaled-tl/build_tl_sourcing_csvs.py" \
  --orders-json "${ROOT}/upscaled-tl/data/techliquidators/orders.json" \
  --out-dir "${ROOT}/upscaled-tl"
"${PYTHON}" "${ROOT}/08_AUTOMATION/CLI_Tools/auction_scraper/sync_techliquidators_order_manifests.py" \
  --cookie-file "${ROOT}/upscaled-tl/data/techliquidators/techliquidators_cookies.txt"
"${PYTHON}" "${ROOT}/08_AUTOMATION/CLI_Tools/auction_scraper/sync_techliquidators_invoices.py" \
  --invoices-dir "${ROOT}/upscaled-tl/TL-invoices" \
  --out "${ROOT}/upscaled-tl/tl_invoices.csv"
"${PYTHON}" "${ROOT}/upscaled-tl/sync_tl_google_sheet.py" \
  --sheet-id "1jNTG59U_hQIGoR4uVu-zNDohfNDmzTKWn-w1PQRkSeA" \
  --creds "/Users/connorodea/.config/upscaled/upscaled-sheets-sync.json" \
  --base-dir "${ROOT}/upscaled-tl" \
  --storage-state "${STORAGE_STATE}"

"${PYTHON}" "${ROOT}/upscaled-tl/sync_tl_google_sheet.py" \
  --sheet-id "1IYNCHK81rTyePOplwFUgl0beP-TLutM6StiuF6rZ7f8" \
  --creds "/Users/connorodea/.config/upscaled/upscaled-sheets-sync.json" \
  --storage-state "${STORAGE_STATE}" \
  --only-bids
