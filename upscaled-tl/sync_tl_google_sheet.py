#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def upsert_sheet(spreadsheet, title: str, rows: list[list[str]]) -> None:
    worksheet = None
    for ws in spreadsheet.worksheets():
        if ws.title.strip().lower() == title.strip().lower():
            worksheet = ws
            break

    if worksheet is None:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1, cols=1)
    elif worksheet.title != title:
        worksheet.update_title(title)

    worksheet.clear()
    if rows:
        worksheet.update(range_name="A1", values=rows, value_input_option="RAW")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync TL sourcing CSVs to Google Sheets."
    )
    parser.add_argument("--sheet-id", required=True, help="Google Sheet ID")
    parser.add_argument(
        "--creds",
        required=True,
        help="Path to service account JSON key",
    )
    parser.add_argument(
        "--orders",
        default="upscaled_tl_sourcing_orders.csv",
        help="Orders CSV filename",
    )
    parser.add_argument(
        "--line-items",
        default="upscaled_tl_sourcing_line_items.csv",
        help="Line items CSV filename",
    )
    parser.add_argument(
        "--summary",
        default="upscaled_tl_sourcing_summary.csv",
        help="Summary CSV filename",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Directory containing the CSV files",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    orders_path = base_dir / args.orders
    line_items_path = base_dir / args.line_items
    summary_path = base_dir / args.summary

    for path in (orders_path, line_items_path, summary_path):
        if not path.exists():
            raise SystemExit(f"Missing file: {path}")

    creds = Credentials.from_service_account_file(args.creds, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(args.sheet_id)

    upsert_sheet(spreadsheet, "Orders", read_csv_rows(orders_path))
    upsert_sheet(spreadsheet, "Line Items", read_csv_rows(line_items_path))
    upsert_sheet(spreadsheet, "Summary", read_csv_rows(summary_path))

    print("Sheet sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
