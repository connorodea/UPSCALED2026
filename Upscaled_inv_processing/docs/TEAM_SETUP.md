Team Setup (Google Drive)

Overview
- Google Drive Shared folder is the source of truth for photo intake/output folders.
- Each user installs the repo locally and points PHOTO_INTAKE_DIR/PHOTO_OUTPUT_DIR to the shared drive.

Recommended Shared folder Paths
- macOS: /Users/<user>/Library/CloudStorage/GoogleDrive-<account>/My Drive/Upscaled2026_SharedDrive
- Windows: C:\Users\<user>\Google Drive\My Drive\Upscaled

macOS (zsh)
1) Install Google Drive for Desktop and ensure the Shared folder is synced.
2) Clone the repo and build:
   - git clone <repo>
   - cd Upscaled_inv_processing
   - npm install
   - npm run build
3) Run the setup script:
   - scripts/setup-drive-macos.sh
4) Reload shell and run:
   - source ~/.zshrc
   - upscaled

Windows (PowerShell)
1) Install Google Drive for Desktop and ensure the Shared folder is synced.
2) Clone the repo and build:
   - git clone <repo>
   - cd Upscaled_inv_processing
   - npm install
   - npm run build
3) Run the setup script:
   - powershell -ExecutionPolicy Bypass -File scripts\setup-drive-windows.ps1
4) Open a new terminal and run:
   - upscaled

Notes
- Photo intake folder: Upscaled_Photo_Intake
- Photo output folder: Upscaled_Photos
- The CLI auto-starts the photo watcher when upscaled launches.
