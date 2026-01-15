#!/usr/bin/env python3
import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build TL sourcing CSVs from orders.json.")
    parser.add_argument(
        "--orders-json",
        default="upscaled-tl/data/techliquidators/orders.json",
        help="Path to orders.json",
    )
    parser.add_argument(
        "--out-dir",
        default="upscaled-tl",
        help="Output directory for CSVs",
    )
    return parser.parse_args()


def parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%B %d, %Y")
    except ValueError:
        return None


def to_float(value) -> float:
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except ValueError:
        return 0.0


def fmt_float(value: float) -> str:
    formatted = f"{value:.2f}"
    formatted = formatted.rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def parse_msrp(title: str) -> float:
    match = re.search(r"orig\.\s*retail\s*\$([\d,]+)", title, re.IGNORECASE)
    if not match:
        return 0.0
    return to_float(match.group(1))


def parse_brands(title: str) -> str:
    if " - " not in title:
        return ""
    parts = title.split(" - ")
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def parse_lot_count(lot_size: str) -> int:
    if not lot_size:
        return 0
    match = re.search(r"\\((\\d+)\\s*Lots?\\)", lot_size, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if "pallet" in lot_size.lower():
        return 1
    return 0


def build_rows(orders: list[dict]) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
    orders_rows = [
        [
            "Date",
            "Order ID",
            "Status",
            "Ship To",
            "Order Total (All-in)",
            "Total MSRP",
            "Total Items",
            "All-in % of MSRP",
            "All-in $/Item",
            "Total Shipping Allocated",
        ]
    ]
    line_items_rows = [
        [
            "Date",
            "Order ID",
            "Category / Title",
            "Brands",
            "Condition",
            "Lot Size",
            "Lots Count",
            "Items Count",
            "MSRP",
            "Lot Price (Ex-Shipping)",
            "Allocated Shipping",
            "All-in Cost",
            "All-in % of MSRP",
            "All-in $/Item",
        ]
    ]

    summary = {
        "orders": 0,
        "msrp": 0.0,
        "items": 0,
        "all_in": 0.0,
    }
    dates = []

    for order in orders:
        order_id = str(order.get("order_id", "")).strip()
        if not order_id:
            continue
        order_date_raw = str(order.get("date", "")).strip()
        order_date = parse_date(order_date_raw)
        if order_date and order_date.year < 2025:
            continue
        if order_date:
            dates.append(order_date)
            date_str = order_date.strftime("%Y-%m-%d")
        else:
            date_str = order_date_raw

        status = str(order.get("status", "")).strip()
        ship_to = str(order.get("ship_to", "")).strip()
        order_total = to_float(order.get("total"))
        items = order.get("items") or []
        sum_item_prices = sum(to_float(item.get("price")) for item in items)
        order_shipping = max(0.0, order_total - sum_item_prices)

        order_total_msrp = 0.0
        order_total_items = 0

        for item in items:
            title = str(item.get("title", "")).strip()
            msrp = parse_msrp(title)
            price = to_float(item.get("price"))
            item_count = int(item.get("item_count") or 0)
            condition = str(item.get("condition", "") or "").strip()
            lot_size = str(item.get("lot_size", "") or "").strip()
            brands = parse_brands(title)
            lots_count = parse_lot_count(lot_size)

            alloc_shipping = 0.0
            if sum_item_prices > 0:
                alloc_shipping = order_shipping * (price / sum_item_prices)
            all_in = price + alloc_shipping
            all_in_pct = (all_in / msrp * 100) if msrp else 0.0
            all_in_per_item = (all_in / item_count) if item_count else 0.0

            line_items_rows.append(
                [
                    date_str,
                    order_id,
                    title,
                    brands,
                    condition,
                    lot_size,
                    str(lots_count) if lots_count else "",
                    str(item_count) if item_count else "",
                    fmt_float(msrp) if msrp else "",
                    fmt_float(price),
                    fmt_float(alloc_shipping),
                    fmt_float(all_in),
                    fmt_float(all_in_pct),
                    fmt_float(all_in_per_item),
                ]
            )

            order_total_msrp += msrp
            order_total_items += item_count

        all_in_pct = (order_total / order_total_msrp * 100) if order_total_msrp else 0.0
        all_in_per_item = (order_total / order_total_items) if order_total_items else 0.0
        orders_rows.append(
            [
                date_str,
                order_id,
                status,
                ship_to,
                fmt_float(order_total),
                fmt_float(order_total_msrp),
                str(order_total_items) if order_total_items else "",
                fmt_float(all_in_pct),
                fmt_float(all_in_per_item),
                fmt_float(order_shipping),
            ]
        )

        summary["orders"] += 1
        summary["msrp"] += order_total_msrp
        summary["items"] += order_total_items
        summary["all_in"] += order_total

    summary_rows = [
        [
            "Period Start",
            "Period End",
            "Total Orders",
            "Total MSRP",
            "Total Items",
            "Total All-in",
            "All-in % of MSRP",
            "All-in $/Item",
        ]
    ]
    if dates:
        start = min(dates).strftime("%Y-%m-%d")
        end = max(dates).strftime("%Y-%m-%d")
    else:
        start = ""
        end = ""
    all_in_pct = (summary["all_in"] / summary["msrp"] * 100) if summary["msrp"] else 0.0
    all_in_per_item = (summary["all_in"] / summary["items"]) if summary["items"] else 0.0
    summary_rows.append(
        [
            start,
            end,
            str(summary["orders"]),
            fmt_float(summary["msrp"]),
            str(summary["items"]) if summary["items"] else "",
            fmt_float(summary["all_in"]),
            fmt_float(all_in_pct),
            fmt_float(all_in_per_item),
        ]
    )

    return orders_rows, line_items_rows, summary_rows


def main() -> int:
    args = parse_args()
    orders_path = Path(args.orders_json)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(orders_path.read_text(encoding="utf-8"))
    orders = data.get("orders") or []
    orders_rows, line_items_rows, summary_rows = build_rows(orders)

    with (out_dir / "upscaled_tl_sourcing_orders.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(orders_rows)
    with (out_dir / "upscaled_tl_sourcing_line_items.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(line_items_rows)
    with (out_dir / "upscaled_tl_sourcing_summary.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(summary_rows)

    print("Wrote TL sourcing CSVs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
