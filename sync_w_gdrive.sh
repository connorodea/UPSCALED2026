SRC="/Users/connorodea/Library/Mobile Documents/com~apple~CloudDocs/Upscaled2026"
DST="gdrive:Upscaled2026"

rclone sync "$SRC" "$DST" \
  --create-empty-src-dirs \
  --drive-chunk-size 64M \
  --transfers 8 \
  --checkers 16 \
  --fast-list \
  --progress

