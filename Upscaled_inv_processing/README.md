# Inventory Processing CLI

An interactive command-line tool for processing inventory with automatic label printing and batch tracking.

## Features

- ✅ Interactive CLI for data entry
- ✅ Automatic SKU generation (format: `GRADE-LOCATION-BATCHID-WAREHOUSETAG`)
- ✅ Batch processing (50 items per batch)
- ✅ CSV data storage
- ✅ Thermal label printing via CUPS
- ✅ QR code generation on labels
- ✅ Label archiving
- ✅ Optional photo intake step with auto-renaming

## Installation

```bash
npm install
npm run build
```

## Usage

### Start the CLI

```bash
npm start
```

Or use the development mode with live reload:

```bash
npm run dev
```

### Start the Web App

```bash
npm run web:dev
```

Then open `http://localhost:8787` for the UI. The CLI remains fully supported.

### One-command local setup

```bash
bash deploy/local_setup.sh
```

## Web App Configuration

Set environment variables before running the web server:

- `UPSCALED_WEB_PASSWORD`: enables password protection for all API routes.
- `UPSCALED_USERS`: JSON array of users (roles: `admin`, `staff`). When set, users must log in with username + password.
- `PRINT_MODE`: `local` (default), `proxy`, or `disabled`.
- `PRINT_PROXY_URL`: when `PRINT_MODE=proxy`, sends label jobs to a local print agent URL.

Example:

```bash
export UPSCALED_WEB_PASSWORD="your-password"
export PRINT_MODE="local"
```

Example multi-user config:

```
UPSCALED_USERS='[{"username":"admin","password":"change-me","role":"admin"},{"username":"staff","password":"change-me","role":"staff"}]'
```

Role permissions:

- `staff`: receive manifest, process items
- `admin`: build hub, export batches

### Printing from a remote web server

If you host the web app on the Hetzner VPS but want printing to happen on a local machine:

1) Run the print agent locally (on the machine with the CUPS printer):

```bash
npm run print:dev
```

2) Point the VPS web server to the local agent (you can tunnel via Tailscale or an SSH reverse proxy):

```bash
export PRINT_MODE="proxy"
export PRINT_PROXY_URL="http://YOUR_LOCAL_MACHINE:8788/print"
```

If the web app runs on the same machine as the printer, set:

```bash
export PRINT_MODE="local"
```

## Deployment

See `Upscaled_inv_processing/deploy/README.md` for Hetzner setup, systemd services, nginx, and SSL.

## SOP

Printable SOP: `http://YOUR_DOMAIN/sop.html`

## Print Agent Installer (macOS unsigned)

Build the installer:

```bash
bash deploy/print_agent/macos/build_macos_print_agent.sh
```

Download from the server:

```
http://YOUR_DOMAIN/downloads/upscaled-print-agent-macos.pkg
```

### Menu Options

1. **Add new product (no photos)** - Enter product information and generate label
2. **Add new product (with photos)** - Enter product information, generate label, then capture photos
3. **View batch status** - See current batch number and item count
4. **Reset batch counter** - Start over from B1UID001
5. **List printers** - View available CUPS printers
6. **Exit** - Close the application

### Product Entry

When adding a product, you'll be prompted for:

- **Grade** (required): LN, VG, G, AC, SA
  - LN = Like New
  - VG = Very Good
  - G = Good
  - AC = Acceptable
  - SA = Salvage

- **UPC** (optional): Product barcode

- **Manufacturer** (optional): Product manufacturer

- **Model** (optional): Model number

- **Warehouse Tag** (optional): Storage location (auto-formatted as BIN###)

### Photo Step (SKU First)

After the label prints, the CLI pauses (only in the "with photos" workflow) so you can apply the SKU label and take photos with the label in the first/last shot. If you set a watch folder, the CLI will automatically collect new photos, rename them to the SKU, and store them under `data/photos/{SKU}`.

Photo environment variables (optional):
- `PHOTO_STEP` (default `true`): set to `false` or `0` to disable
- `PHOTO_WATCH_DIR`: folder where the camera drops new files
- `PHOTO_OUTPUT_DIR` (default `data/photos`)
- `PHOTO_MIN_COUNT` (default `1`)
- `PHOTO_IDLE_MS` (default `1500`)
- `PHOTO_TIMEOUT_MS` (default `120000`)

### SKU Format

Generated SKUs follow this pattern:
```
GRADE-LOCATION-BATCHID-WAREHOUSETAG
```

Example: `LN-DEN001-B1UID001-BIN001`

- Grade: Product condition code
- Location: Fixed as DEN001
- Batch ID: Format B{batch}UID{item} (e.g., B1UID001, B1UID050, B2UID001)
- Warehouse Tag: Optional bin location

### Batch Processing

- Batches contain 50 items each
- Batch IDs increment automatically: B1UID001 → B1UID050 → B2UID001
- Batch state persists between sessions
- Can be reset via menu option

## Output Files

### CSV Data
- Location: `data/inventory.csv`
- Contains: SKU, grade, location, batch ID, warehouse tag, UPC, manufacturer, model, timestamp

### Labels
- Location: `labels/`
- Format: PNG images (2" x 1" / 51x25mm)
- Filename: `{SKU}.png`
- Contents: QR code, SKU, grade, product details

## Printer Setup

The system uses CUPS for printing. Ensure your thermal printer is configured:

1. Add printer to CUPS:
   ```bash
   sudo lpadmin -p ThermalPrinter -E -v usb://YOUR_PRINTER
   ```

2. Set as default (optional):
   ```bash
   lpoptions -d ThermalPrinter
   ```

3. Verify printer:
   ```bash
   lpstat -p
   ```

The CLI will auto-detect your default CUPS printer. If no printer is found, labels will still be saved to the `labels/` directory for manual printing.

## Printer Compatibility

Tested with:
- Generic ESC/POS thermal printers
- CUPS-compatible label printers
- Brother QL series
- Zebra desktop printers

## Label Specifications

- Size: 2" x 1" (51mm x 25mm)
- DPI: 203
- Format: PNG
- Features:
  - QR code with SKU (left side)
  - Full SKU text (bold)
  - Grade information
  - Product details (manufacturer/model)
  - UPC (if provided)

## Directory Structure

```
.
├── src/                   # TypeScript source files
│   ├── index.ts          # Main CLI application
│   ├── batchManager.ts   # Batch tracking logic
│   ├── csvStorage.ts     # CSV file handling
│   ├── labelGenerator.ts # Label image generation
│   ├── photoManager.ts   # Photo intake and renaming
│   ├── printer.ts        # CUPS printer integration
│   ├── skuGenerator.ts   # SKU formatting
│   └── types.ts          # TypeScript interfaces
├── data/                  # CSV data storage
│   ├── inventory.csv     # Product records
│   └── batch-state.json  # Batch counter state
├── labels/               # Generated label images
└── dist/                 # Compiled JavaScript
```

## Troubleshooting

### Printer not detected
- Check CUPS status: `lpstat -p`
- Verify printer is enabled: `cupsenable PRINTER_NAME`
- Check printer queue: `lpstat -o`

### Labels not printing
- Labels are saved in `labels/` directory
- Print manually: `lp -d PRINTER_NAME labels/SKU.png`
- Verify printer supports PNG files

### Batch counter issues
- Batch state saved in: `data/batch-state.json`
- Manually edit or delete to reset
- Use "Reset batch counter" menu option

## Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Build for production
npm run build

# Run built version
npm start
```

## License

MIT
