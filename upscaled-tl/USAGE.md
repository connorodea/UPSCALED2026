# Upscaled TL Usage Guide

Last updated: 2026-01-15

## Quick start

1) Refresh TL cookies (interactive login, saves cookies after ~25s):
```
upscaled-tl auth
```

2) Run full sync (orders, manifests, invoices, sheets):
```
upscaled-tl sync
```

## Commands

### `upscaled-tl auth`
Refresh TechLiquidators cookies (uses Playwright). Required when orders fetch starts failing.

### `upscaled-tl sync`
Runs the full TL sync pipeline:
- fetch orders
- rebuild sourcing CSVs
- download order manifests
- parse invoices
- sync Google Sheets

### `upscaled-tl orders`
Fetch latest orders into `upscaled-tl/data/techliquidators/orders.json`.

### `upscaled-tl invoices`
Parse invoice PDFs from `upscaled-tl/TL-invoices` into `upscaled-tl/tl_invoices.csv`.

### `upscaled-tl -h`
Show help.

## Data locations

- TL data (cookies, orders, manifests): `upscaled-tl/data/techliquidators`
- TL invoices (PDFs): `upscaled-tl/TL-invoices`
- Invoices CSV: `upscaled-tl/tl_invoices.csv`
- Sourcing CSVs:
  - `upscaled-tl/upscaled_tl_sourcing_orders.csv`
  - `upscaled-tl/upscaled_tl_sourcing_line_items.csv`
  - `upscaled-tl/upscaled_tl_sourcing_summary.csv`

## Notes

- Orders before 2025 are excluded.
- Master Manifest aggregates all tabs in each order manifest (.xlsx).
- Invoices tab auto-populates status dropdown and sets Payments Applied = Total Due when Status = Paid.
- Cookies are only refreshed when you run `upscaled-tl auth`.

