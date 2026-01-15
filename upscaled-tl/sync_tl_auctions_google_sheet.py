#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def upsert_sheet(spreadsheet, title: str, rows: List[List[str]]) -> None:
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


def ensure_summary_template(spreadsheet, rows: int = 52) -> None:
    title = "Summary"
    worksheet = None
    for ws in spreadsheet.worksheets():
        if ws.title.strip().lower() == title.lower():
            worksheet = ws
            break
    if worksheet is None:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1, cols=1)
    elif worksheet.title != title:
        worksheet.update_title(title)

    existing = worksheet.get_all_values()
    if existing:
        return

    rates = [0.12, 0.15, 0.18, 0.21, 0.24, 0.27, 0.30]
    headers = [
        "Week Start",
        "Week End",
        "Total MSRP",
        "All-in Cost %",
        "All-in Cost $",
        "Notes",
    ]
    for rate in rates:
        pct = int(rate * 100)
        headers.extend([f"Net @ {pct}%", f"You @ {pct}%", f"Sam @ {pct}%"])

    template = [headers]
    for row in range(2, rows + 2):
        base = [
            "",
            "",
            "",
            "",
            f"=IF($C{row}=\"\",\"\",$C{row}*$D{row})",
            "",
        ]
        for rate in rates:
            net = f"=IF($C{row}=\"\",\"\",MAX(0,($C{row}*{rate})-$E{row}))"
            you = f"=IF($C{row}=\"\",\"\",MAX(0,($C{row}*{rate})-$E{row})*0.4)"
            sam = f"=IF($C{row}=\"\",\"\",MAX(0,($C{row}*{rate})-$E{row})*0.6)"
            base.extend([net, you, sam])
        template.append(base)

    worksheet.update(range_name="A1", values=template, value_input_option="USER_ENTERED")


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_watchlist_rows(payload: Dict[str, Any]) -> List[List[str]]:
    headers = [
        "fetched_at",
        "source_url",
        "auction_id",
        "url",
        "title",
        "current_bid_value",
        "lot_price_value",
        "msrp_value",
        "retail_value_value",
        "items_count_value",
        "shipping_cost_value",
        "condition",
        "warehouse",
        "auction_end",
        "manifest_url",
        "manifest_path",
        "detail_path",
    ]
    rows = [headers]
    fetched_at = payload.get("fetched_at")
    source_url = payload.get("source_url")
    for item in payload.get("items", []):
        rows.append(
            [
                to_str(fetched_at),
                to_str(source_url),
                to_str(item.get("auction_id")),
                to_str(item.get("url")),
                to_str(item.get("title")),
                to_str(item.get("current_bid_value")),
                to_str(item.get("lot_price_value")),
                to_str(item.get("msrp_value")),
                to_str(item.get("retail_value_value")),
                to_str(item.get("items_count_value")),
                to_str(item.get("shipping_cost_value")),
                to_str(item.get("condition")),
                to_str(item.get("warehouse")),
                to_str(item.get("auction_end")),
                to_str(item.get("manifest_url")),
                to_str(item.get("manifest_path")),
                to_str(item.get("detail_path")),
            ]
        )
    return rows


def build_manifest_rows(payload: Dict[str, Any]) -> List[List[str]]:
    headers = [
        "auction_id",
        "title",
        "manifest_path",
        "row_count",
        "msrp_total",
        "avg_msrp",
        "msrp_column",
        "quantity_column",
        "description_column",
        "brand_column",
        "category_column",
        "top_brands_json",
        "top_categories_json",
        "sample_items_json",
    ]
    rows = [headers]
    for item in payload.get("items", []):
        summary = item.get("manifest_summary") or {}
        rows.append(
            [
                to_str(item.get("auction_id")),
                to_str(item.get("title")),
                to_str(item.get("manifest_path")),
                to_str(summary.get("row_count")),
                to_str(summary.get("msrp_total")),
                to_str(summary.get("avg_msrp")),
                to_str(summary.get("msrp_column")),
                to_str(summary.get("quantity_column")),
                to_str(summary.get("description_column")),
                to_str(summary.get("brand_column")),
                to_str(summary.get("category_column")),
                to_str(summary.get("top_brands")),
                to_str(summary.get("top_categories")),
                to_str(summary.get("sample_items")),
            ]
        )
    return rows


def build_bids_rows(payload: Dict[str, Any]) -> List[List[str]]:
    headers = [
        "fetched_at",
        "source_url",
        "auction_id",
        "lot_id",
        "url",
        "title",
        "current_bid_value",
        "my_max_bid_value",
        "bid_status",
        "units",
        "closes_in",
        "auction_end",
    ]
    rows = [headers]
    fetched_at = payload.get("fetched_at")
    source_url = payload.get("source_url")
    for item in payload.get("items", []):
        rows.append(
            [
                to_str(fetched_at),
                to_str(source_url),
                to_str(item.get("auction_id")),
                to_str(item.get("lot_id")),
                to_str(item.get("url")),
                to_str(item.get("title")),
                to_str(item.get("current_bid_value")),
                to_str(item.get("my_max_bid_value")),
                to_str(item.get("bid_status")),
                to_str(item.get("units")),
                to_str(item.get("closes_in")),
                to_str(item.get("auction_end")),
            ]
        )
    return rows


def build_analysis_rows(payload: List[Dict[str, Any]]) -> List[List[str]]:
    headers = [
        "auctionId",
        "title",
        "decision",
        "ruleDecision",
        "estimatedResaleValue",
        "estimatedProfit",
        "estimatedMargin",
        "costBasis",
        "msrpTotal",
        "inboundShipping",
        "outboundShipping",
        "marketplaceFees",
        "laborCost",
        "warehouseCost",
    ]
    rows = [headers]
    for item in payload:
        rows.append([to_str(item.get(key)) for key in headers])
    return rows


def build_items_rows(items_dir: Path) -> List[List[str]]:
    headers = [
        "pallet_id",
        "lot_id",
        "title",
        "url",
        "channel",
        "status",
        "condition",
        "lot_size",
        "total_quantity",
        "extended_msrp_cents",
        "asking_price_cents",
        "initial_asking_price_cents",
        "shipping_cost_cents",
        "shipping_cost_final_cents",
        "shipping_cost_discount_cents",
        "warehouse_city",
        "warehouse_state",
        "warehouse_zip",
        "auction_id",
        "auction_starts_at",
        "auction_ends_at",
        "current_price_cents",
        "number_of_bids",
        "winning_bid_amount_cents",
        "runner_up_bid_amount_cents",
        "created_at",
        "updated_at",
        "primary_photo",
        "top_categories_json",
    ]
    rows = [headers]
    for path in sorted(items_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pallet = data.get("pallet") or {}
        auction = pallet.get("auction") or {}
        lot_id = pallet.get("name")
        detail_path = pallet.get("path")
        url = f"https://www.techliquidators.com{detail_path}" if detail_path else ""
        rows.append(
            [
                to_str(pallet.get("id")),
                to_str(lot_id),
                to_str(pallet.get("title")),
                to_str(url),
                to_str(pallet.get("channel")),
                to_str(pallet.get("status")),
                to_str(pallet.get("condition")),
                to_str(pallet.get("lot_size")),
                to_str(pallet.get("total_quantity")),
                to_str(pallet.get("extended_msrp_cents")),
                to_str(pallet.get("asking_price_cents")),
                to_str(pallet.get("initial_asking_price_cents")),
                to_str(pallet.get("shipping_cost_cents")),
                to_str(pallet.get("shipping_cost_final_cents")),
                to_str(pallet.get("shipping_cost_discount_cents")),
                to_str(pallet.get("warehouse_city")),
                to_str(pallet.get("warehouse_state")),
                to_str(pallet.get("warehouse_zip")),
                to_str(auction.get("auction_id")),
                to_str(auction.get("auction_starts_at")),
                to_str(auction.get("auction_ends_at")),
                to_str(auction.get("current_price_cents")),
                to_str(auction.get("number_of_bids")),
                to_str(auction.get("winning_bid_amount_cents")),
                to_str(auction.get("runner_up_bid_amount_cents")),
                to_str(pallet.get("created_at")),
                to_str(pallet.get("updated_at")),
                to_str(pallet.get("primary_photo")),
                to_str(pallet.get("top_categories")),
            ]
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync TechLiquidators auctions data to Google Sheets."
    )
    parser.add_argument("--sheet-id", required=True, help="Google Sheet ID")
    parser.add_argument("--creds", required=True, help="Path to service account JSON key")
    parser.add_argument(
        "--data-dir",
        default="upscaled-tl/data/techliquidators",
        help="TechLiquidators data directory",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    watchlist_path = data_dir / "watchlist.json"
    bids_path = data_dir / "bids.json"
    analysis_path = data_dir / "analysis.json"
    items_dir = data_dir / "items"

    creds = Credentials.from_service_account_file(args.creds, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(args.sheet_id)

    watchlist_payload = load_json(watchlist_path)
    if watchlist_payload:
        upsert_sheet(spreadsheet, "Watchlist", build_watchlist_rows(watchlist_payload))
        upsert_sheet(spreadsheet, "Manifest Summary", build_manifest_rows(watchlist_payload))
    else:
        upsert_sheet(spreadsheet, "Watchlist", [["message"], ["watchlist.json not found"]])
        upsert_sheet(spreadsheet, "Manifest Summary", [["message"], ["watchlist.json not found"]])

    bids_payload = load_json(bids_path)
    if bids_payload:
        upsert_sheet(spreadsheet, "Bids", build_bids_rows(bids_payload))
    else:
        upsert_sheet(spreadsheet, "Bids", [["message"], ["bids.json not found"]])

    analysis_payload = load_json(analysis_path)
    if analysis_payload:
        upsert_sheet(spreadsheet, "Analysis", build_analysis_rows(analysis_payload))
    else:
        upsert_sheet(spreadsheet, "Analysis", [["message"], ["analysis.json not found"]])

    if items_dir.exists():
        upsert_sheet(spreadsheet, "Items", build_items_rows(items_dir))
    else:
        upsert_sheet(spreadsheet, "Items", [["message"], ["items/ directory not found"]])

    ensure_summary_template(spreadsheet)

    print("TL auctions sheet sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
