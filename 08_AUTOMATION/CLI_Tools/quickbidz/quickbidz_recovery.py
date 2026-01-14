#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


CARD_START = 'class="card listing-card lot-card"'
RETAIL_RE = re.compile(r'retail-price-amount">\\s*\\$\\s*([0-9,]+(?:\\.[0-9]{2})?)')
FINAL_RE = re.compile(r'au-price price[\\s\\S]*?\\$\\s*([0-9,]+(?:\\.[0-9]{2})?)')
LISTING_URL_RE = re.compile(r'href="(https://www\\.quickbidz\\.com/listing/[^"]+)"')


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_cards(html: str) -> List[Tuple[float, float, Optional[str]]]:
    cards: List[Tuple[float, float, Optional[str]]] = []
    starts = [m.start() for m in re.finditer(CARD_START, html)]
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(html)
        block = html[start:end]
        retail_match = RETAIL_RE.search(block)
        final_match = FINAL_RE.search(block)
        if not retail_match or not final_match:
            continue
        retail = float(retail_match.group(1).replace(",", ""))
        final = float(final_match.group(1).replace(",", ""))
        url_match = LISTING_URL_RE.search(block)
        listing_url = url_match.group(1) if url_match else None
        cards.append((retail, final, listing_url))
    return cards


def detect_max_page(html: str) -> int:
    start = html.lower().find("pagination")
    if start == -1:
        return 1
    block = html[start : start + 2500]
    pages = [int(p) for p in re.findall(r"page=(\\d+)", block)]
    return max(pages) if pages else 1


def normalize_url(url: str, page: int, limit: Optional[int]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if page is not None:
        query["page"] = str(page)
    if limit is not None:
        query["limit"] = str(limit)
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def category_slug_from_listing(url: str) -> Optional[str]:
    try:
        html = fetch_html(url)
    except requests.RequestException:
        return None
    m = re.search(r'<nav aria-label="breadcrumb"[\\s\\S]*?</nav>', html)
    if not m:
        return None
    nav = m.group(0)
    m2 = re.search(r"https://www\\.quickbidz\\.com/category/([a-z0-9\\-]+)", nav)
    return m2.group(1) if m2 else None


def normalize_category(value: str) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    aliases = {
        "electronics": "electronics-appliances",
        "appliances": "electronics-appliances",
        "electronics-appliances": "electronics-appliances",
        "miscellaneous": "miscellaneous",
    }
    return aliases.get(normalized, normalized)


def aggregate_cards(cards: Iterable[Tuple[float, float, Optional[str]]]) -> Dict[str, float]:
    retail_total = 0.0
    final_total = 0.0
    count = 0
    for retail, final, _ in cards:
        retail_total += retail
        final_total += final
        count += 1
    recovery = (final_total / retail_total * 100) if retail_total else 0.0
    return {
        "count": count,
        "retail_total": retail_total,
        "final_total": final_total,
        "recovery_pct": recovery,
    }


def format_money(value: float) -> str:
    return f"${value:,.2f}"


def print_report(
    *,
    label: str,
    count: int,
    retail_total: float,
    final_total: float,
    recovery_pct: float,
    method: str,
) -> None:
    print(f"Here’s the recovery for {label}:")
    print("")
    print(f"- Listings counted: {count}")
    print(f"- Total retail: {format_money(retail_total)}")
    print(f"- Total final price: {format_money(final_total)}")
    print(f"- Recovery percentage: {recovery_pct:.2f}%")
    print("")
    print(f"Method: {method}")


def log_run(
    *,
    log_path: str,
    url: str,
    category: Optional[str],
    mode: str,
    count: int,
    retail_total: float,
    final_total: float,
    recovery_pct: float,
) -> None:
    timestamp = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    row = {
        "timestamp_utc": timestamp,
        "url": url,
        "category": category or "",
        "mode": mode,
        "items_count": str(count),
        "retail_total": f"{retail_total:.2f}",
        "final_total": f"{final_total:.2f}",
        "recovery_pct": f"{recovery_pct:.2f}",
    }
    write_header = False
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            write_header = f.tell() == 0
    except FileNotFoundError:
        write_header = True

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute Quickbidz recovery percentage from auction listing cards.",
        epilog=(
            "Examples:\n"
            "  upscaled-quickbidz --url \"https://www.quickbidz.com/live-auction/dfw-tx-24hour-auction/207919\"\n"
            "  upscaled-quickbidz --url \"https://www.quickbidz.com/live-auction/dfw-tx-24hour-auction/207919\" "
            "--category electronics\n"
            "  upscaled-quickbidz --url \"https://www.quickbidz.com/past-auctions/?limit=80\" --pages 10\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", required=True, help="Quickbidz auction URL")
    parser.add_argument("--limit", type=int, default=None, help="Items per page (past auctions)")
    parser.add_argument("--pages", type=int, default=None, help="Max pages to scrape (past auctions)")
    parser.add_argument("--concurrency", type=int, default=6, help="Parallel requests (past auctions)")
    parser.add_argument(
        "--category",
        help="Filter live auction listings by category (electronics, appliances, miscellaneous).",
    )
    parser.add_argument(
        "--category-slug",
        help="Filter live auction listings by category slug (legacy; use --category).",
    )
    parser.add_argument(
        "--log-file",
        default="08_AUTOMATION/CLI_Tools/quickbidz/quickbidz_runs.csv",
        help="CSV log file path for tracking runs.",
    )
    args = parser.parse_args()

    url = args.url.strip()
    category = normalize_category(args.category) if args.category else None
    if not category and args.category_slug:
        category = normalize_category(args.category_slug)

    if "/live-auction/" in url:
        html = fetch_html(url)
        cards = parse_cards(html)
        label = "the auction"
        method = "pulled retail + current price from the auction page cards"
        if category:
            target = category
            filtered: List[Tuple[float, float, Optional[str]]] = []
            with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
                futures = {}
                for retail, final, listing_url in cards:
                    if not listing_url:
                        continue
                    futures[ex.submit(category_slug_from_listing, listing_url)] = (retail, final, listing_url)
                for fut in as_completed(futures):
                    retail, final, listing_url = futures[fut]
                    slug = fut.result()
                    if slug == target:
                        filtered.append((retail, final, listing_url))
            cards = filtered
            label = f"{target} in that auction"
            method = (
                "pulled retail + current price from the auction page cards, "
                "then filtered by listing-page breadcrumb category slug"
            )
        result = aggregate_cards(cards)
        print_report(
            label=label,
            count=int(result["count"]),
            retail_total=result["retail_total"],
            final_total=result["final_total"],
            recovery_pct=result["recovery_pct"],
            method=method,
        )
        log_run(
            log_path=args.log_file,
            url=url,
            category=category,
            mode="live-auction",
            count=int(result["count"]),
            retail_total=result["retail_total"],
            final_total=result["final_total"],
            recovery_pct=result["recovery_pct"],
        )
        return 0

    if category:
        url = normalize_url(url, page=1, limit=args.limit)
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["category_slug"] = category
        url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    first_url = normalize_url(url, page=1, limit=args.limit)
    first_html = fetch_html(first_url)
    max_page = detect_max_page(first_html)
    if args.pages is not None:
        max_page = min(max_page, args.pages)

    all_cards: List[Tuple[float, float, Optional[str]]] = []
    all_cards.extend(parse_cards(first_html))

    def fetch_page(page: int) -> List[Tuple[float, float, Optional[str]]]:
        page_url = normalize_url(url, page=page, limit=args.limit)
        html = fetch_html(page_url)
        return parse_cards(html)

    if max_page > 1:
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futures = {ex.submit(fetch_page, page): page for page in range(2, max_page + 1)}
            for fut in as_completed(futures):
                all_cards.extend(fut.result())

    result = aggregate_cards(all_cards)
    method = "pulled retail + final price from the past-auctions listing cards"
    label = "the search results"
    print_report(
        label=label,
        count=int(result["count"]),
        retail_total=result["retail_total"],
        final_total=result["final_total"],
        recovery_pct=result["recovery_pct"],
        method=method,
    )
    log_run(
        log_path=args.log_file,
        url=url,
        category=category,
        mode="past-auctions",
        count=int(result["count"]),
        retail_total=result["retail_total"],
        final_total=result["final_total"],
        recovery_pct=result["recovery_pct"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
