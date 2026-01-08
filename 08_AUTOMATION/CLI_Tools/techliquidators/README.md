# TechLiquidators Auction CLI

Fetches auction data from TechLiquidators, saves the raw HTML, and writes a normalized JSON + CSV summary for metrics.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python tl_auction_fetch.py \
  --url "https://www.techliquidators.com/detail/ml29530756/ice-makers-ge-profile-insignia/"
```

By default this creates a folder in `01_SOURCING/Auctions/<year>/` named `TL_<auction_id>_<slug>` and saves:

- `raw.html`
- `auction.json`
- `auction.csv`
- `manifest.xlsx` (when `--manifest` is used and available)

## Options

- `--out-base`: change the base output directory
- `--year`: override the year folder
- `--folder-name`: custom folder name
- `--raw-only`: only save raw HTML
- `--manifest`: download the manifest XLSX if available
