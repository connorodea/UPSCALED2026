# Auction Scraper (TechLiquidators + Liquidation.com)

Scrapes auction listings, downloads detail pages, extracts key fields, and saves manifests when available.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

TechLiquidators (all auctions):

```bash
python scrape_auctions.py --site techliquidators --manifest --resume
```

Liquidation.com (FergusonHome only):

```bash
python scrape_auctions.py --site liquidation --manifest --resume
```

If Liquidation.com blocks requests (403), export cookies from your browser and pass them in:

```bash
python get_liquidation_cookies.py --browser chrome --out liquidation_cookies.txt
python scrape_auctions.py --site liquidation --manifest --cookie-file liquidation_cookies.txt
```

## TechLiquidators Watchlist

Export cookies (requires Playwright):

```bash
pip install playwright
playwright install
python get_techliquidators_cookies.py
```

Sync watchlist items + manifests into the inventory CLI data folder:

```bash
python sync_techliquidators_watchlist.py --cookie-file upscaled-tl/data/techliquidators/techliquidators_cookies.txt
```

## TechLiquidators My Bids

Sync your My Bids items into the inventory CLI data folder:

```bash
python sync_techliquidators_bids.py --cookie-file upscaled-tl/data/techliquidators/techliquidators_cookies.txt
```

Options:

- `--bids-url`: override the My Bids URL

## Master Manifest (Won Auctions)

The inventory CLI tracks won manifests in `Upscaled_inv_processing/data/manifests.json`.
To aggregate won auctions + line items into a master manifest:

```bash
python build_master_manifest.py
```

Outputs:

- `01_SOURCING/Auctions/master_manifest/master_manifest.csv`
- `01_SOURCING/Auctions/master_manifest/master_line_items.csv`
- `01_SOURCING/Inventory_Hub/inventory_unprocessed.csv`
- `01_SOURCING/Inventory_Hub/inventory_processed.csv`

You can also add headers:

```bash
python scrape_auctions.py --site liquidation --header "Referer: https://www.liquidation.com/"
```

## Output

Data is saved under:

```
01_SOURCING/Auctions/<site>/<year>/
```

Each auction gets:

- `raw.html`
- `auction.json`
- `auction.csv`
- `manifest.xlsx` (if available and `--manifest` is used)

An index is written to:

- `01_SOURCING/Auctions/<site>/<year>/index.jsonl`
- `01_SOURCING/Auctions/<site>/<year>/index.csv`

## Options

- `--start-url`: override the listing start URL (use multiple times)
- `--max-pages`: limit listing pages crawled
- `--max-auctions`: limit auctions scraped
- `--delay`: delay between requests (seconds)
- `--manifest`: download manifests when available
- `--resume`: skip auctions already in `index.jsonl`
