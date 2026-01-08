#!/usr/bin/env bash
set -euo pipefail

repo_default="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
read -r -p "Repo path [${repo_default}]: " repo_input
repo_dir="${repo_input:-$repo_default}"

echo "Example Google Drive path:"
echo "  /Users/$USER/Library/CloudStorage/GoogleDrive-<account>/My Drive/Upscaled2026_SharedDrive"
read -r -p "Google Drive base folder: " drive_root
if [[ -z "${drive_root}" ]]; then
  echo "Drive root is required."
  exit 1
fi

intake_dir="${drive_root}/Upscaled_Photo_Intake"
output_dir="${drive_root}/Upscaled_Photos"

mkdir -p "${intake_dir}" "${output_dir}"

mkdir -p "${HOME}/.local/bin"
cat <<EOW > "${HOME}/.local/bin/upscaled"
#!/usr/bin/env bash
set -euo pipefail
cd "${repo_dir}"
node "${repo_dir}/dist/index.js" "\$@"
EOW
chmod +x "${HOME}/.local/bin/upscaled"

python3 - <<PY
from pathlib import Path

intake_dir = "${intake_dir}"
output_dir = "${output_dir}"
zshrc = Path.home() / ".zshrc"
text = zshrc.read_text() if zshrc.exists() else ""
lines = text.splitlines()
block_header = "# Upscaled shortcuts"
out = []
skip = False
for line in lines:
    if line.strip() == block_header:
        skip = True
        continue
    if skip:
        if line.strip() == "":
            skip = False
            out.append(line)
        continue
    out.append(line)

updated = "\n".join(out).rstrip("\n")
block = (
    "\n\n# Upscaled shortcuts\n"
    f'export PHOTO_INTAKE_DIR="{intake_dir}"\n'
    f'export PHOTO_OUTPUT_DIR="{output_dir}"\n'
    'export PATH="$HOME/.local/bin:$PATH"\n'
    f'alias upscaled-photos="open \\\"{output_dir}\\\""\n'
    f'alias upscaled-install="/Users/connorodea/Library/Mobile Documents/com~apple~CloudDocs/UPSCALED2026/Upscaled_inv_processing/install.sh"
alias upscaled-intake="open \\\"{intake_dir}\\\""\n'
)
zshrc.write_text(updated + block)
PY

cat <<EOT
Done.
- Intake: ${intake_dir}
- Output: ${output_dir}

Next:
1) source ~/.zshrc
2) cd "${repo_dir}" && npm install && npm run build
3) run: upscaled
EOT
