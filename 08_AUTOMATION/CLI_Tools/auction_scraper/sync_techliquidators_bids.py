#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scrape_auctions import USER_AGENT, TECHLIQUIDATORS_PATTERN, extract_techliquidators_id


BIDS_URLS = [
    "https://www.techliquidators.com/account/bids",
    "https://www.techliquidators.com/account/bids?page=1",
    "https://www.techliquidators.com/account/my-bids",
    "https://www.techliquidators.com/my-bids",
    "https://www.techliquidators.com/bids",
]

API_URLS = [
    "https://www.techliquidators.com/api/account/bids",
    "https://www.techliquidators.com/api/account/my-bids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync TechLiquidators My Bids items."
    )
    parser.add_argument("--cookie-file", help="Netscape cookie file for TechLiquidators")
    parser.add_argument("--cookie-header", help="Raw Cookie header value")
    parser.add_argument("--bids-url", help="Override bids URL")
    parser.add_argument("--out-dir", default="upscaled-tl/data/techliquidators")
    parser.add_argument("--max-items", type=int, default=0)
    return parser.parse_args()


def find_project_root(start: str) -> Optional[str]:
    current = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(current, "01_SOURCING")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    root = find_project_root(os.getcwd()) or find_project_root(os.path.dirname(__file__))
    if root:
        return os.path.join(root, path)
    return path


def load_cookie_jar(cookie_file: str) -> Optional[requests.cookies.RequestsCookieJar]:
    try:
        jar = requests.cookies.RequestsCookieJar()
        with open(cookie_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.strip().split("\t")
                if len(parts) < 7:
                    continue
                domain, _, path, secure, _, name, value = parts[:7]
                jar.set(name, value, domain=domain, path=path, secure=secure.lower() == "true")
        return jar
    except FileNotFoundError:
        return None


def get_bids_html(session: requests.Session, url: str) -> Optional[str]:
    try:
        resp = session.get(url, timeout=30)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    if "/login" in resp.url:
        return None
    return resp.text


def normalize_header(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.strip().lower())
    return re.sub(r"\s+", " ", cleaned)


def parse_currency(value: str) -> Optional[float]:
    cleaned = value.replace(",", "").replace("$", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int(value: str) -> Optional[int]:
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def parse_duration_to_ms(value: str) -> Optional[int]:
    if not value:
        return None
    text = value.strip().lower()
    if "ended" in text or "closed" in text:
        return 0
    matches = list(re.finditer(r"(\d+)\s*([dhm])", text))
    if matches:
        total_ms = 0
        for match in matches:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit == "d":
                total_ms += amount * 24 * 60 * 60 * 1000
            elif unit == "h":
                total_ms += amount * 60 * 60 * 1000
            else:
                total_ms += amount * 60 * 1000
        return total_ms
    matches = list(re.finditer(r"(\d+)\s*(day|days|hour|hours|hr|hrs|minute|minutes|min|mins)", text))
    if matches:
        total_ms = 0
        for match in matches:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit.startswith("day"):
                total_ms += amount * 24 * 60 * 60 * 1000
            elif unit.startswith("hour") or unit.startswith("hr"):
                total_ms += amount * 60 * 60 * 1000
            else:
                total_ms += amount * 60 * 1000
        return total_ms
    return None


def parse_bids_table(html: str, base_url: str, fetched_at: dt.datetime) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    table = None
    header_map: Dict[int, str] = {}
    for candidate in soup.find_all("table"):
        header_cells = candidate.find_all("th")
        if not header_cells:
            continue
        candidate_map = {}
        for idx, cell in enumerate(header_cells):
            candidate_map[idx] = normalize_header(cell.get_text(" ", strip=True))
        headers = " ".join(candidate_map.values())
        if "lot id" in headers or "auction id" in headers or "closes in" in headers:
            table = candidate
            header_map = candidate_map
            break

    if not table:
        return []

    items = []
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue
        data: Dict[str, str] = {}
        for idx, cell in enumerate(cells):
            header = header_map.get(idx, "")
            text = cell.get_text(" ", strip=True)
            if header:
                data[header] = text

        link = None
        for a_tag in row.find_all("a", href=True):
            href = a_tag.get("href")
            if href and TECHLIQUIDATORS_PATTERN.search(href):
                link = urljoin(base_url, href)
                break

        lot_id = data.get("lot id") or data.get("lot") or data.get("auction id")
        auction_id = extract_techliquidators_id(link or "") or (lot_id.lower() if lot_id else None)

        closes_in = data.get("closes in") or data.get("closes") or data.get("close in")
        duration_ms = parse_duration_to_ms(closes_in or "")
        auction_end = None
        if duration_ms is not None:
            auction_end = (fetched_at + dt.timedelta(milliseconds=duration_ms)).isoformat()

        item = {
            "auction_id": auction_id.upper() if auction_id else None,
            "lot_id": lot_id,
            "url": link,
            "title": data.get("title") or data.get("description"),
            "current_bid_value": parse_currency(data.get("winning bid", "") or data.get("current bid", "")),
            "my_max_bid_value": parse_currency(data.get("my max bid", "")),
            "bid_status": data.get("bid status"),
            "units": parse_int(data.get("units", "")),
            "closes_in": closes_in,
            "auction_end": auction_end,
        }

        items.append(item)

    return items


def main() -> int:
    args = parse_args()
    out_dir = resolve_path(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    if args.cookie_header:
        session.headers.update({"Cookie": args.cookie_header})
    elif args.cookie_file:
        jar = load_cookie_jar(resolve_path(args.cookie_file))
        if jar:
            session.cookies.update(jar)

    fetched_at = dt.datetime.now(dt.timezone.utc)
    bids_url = args.bids_url

    items: List[Dict[str, object]] = []
    api_items = None
    api_source_url = None
    source_url = None
    for url in API_URLS:
        try:
            resp = session.get(url, timeout=30)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        try:
            data = resp.json()
        except ValueError:
            continue
        if isinstance(data, list):
            api_items = data
            api_source_url = url
            break

    if api_items:
        for entry in api_items:
            if not isinstance(entry, dict):
                continue
            path_value = entry.get("path") or entry.get("url")
            url = urljoin("https://www.techliquidators.com", path_value) if path_value else None
            auction_id = entry.get("auction_id") or entry.get("name") or entry.get("id")
            closes_in = entry.get("closes_in") or entry.get("closesIn")
            auction_end = entry.get("auction_ends_at") or entry.get("auctionEnd")
            if not auction_end and closes_in:
                duration_ms = parse_duration_to_ms(str(closes_in))
                if duration_ms is not None:
                    auction_end = (fetched_at + dt.timedelta(milliseconds=duration_ms)).isoformat()
            item = {
                "auction_id": str(auction_id).upper() if auction_id else None,
                "lot_id": entry.get("lot_id") or entry.get("lotId"),
                "url": url,
                "title": entry.get("title") or entry.get("name"),
                "current_bid_value": (entry.get("current_price_cents") or 0) / 100 if entry.get("current_price_cents") else None,
                "my_max_bid_value": (entry.get("my_max_bid_cents") or 0) / 100 if entry.get("my_max_bid_cents") else None,
                "bid_status": entry.get("bid_status") or entry.get("status"),
                "units": entry.get("units") or entry.get("quantity"),
                "closes_in": closes_in,
                "auction_end": auction_end,
            }
            items.append(item)
    else:
        bids_urls = [bids_url] if bids_url else []
        bids_urls.extend(BIDS_URLS)
        bids_html = None
        for url in bids_urls:
            html = get_bids_html(session, url)
            if html:
                bids_html = html
                source_url = url
                break

        if not bids_html:
            print("Failed to load TechLiquidators My Bids page. Check cookies and URL.", file=sys.stderr)
            return 1

        items = parse_bids_table(bids_html, source_url or "", fetched_at)

    if args.max_items and args.max_items > 0:
        items = items[: args.max_items]

    payload = {
        "fetched_at": fetched_at.isoformat(),
        "source_url": bids_url or api_source_url or source_url,
        "items": items,
    }

    bids_path = os.path.join(out_dir, "bids.json")
    with open(bids_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {len(items)} bid items to {bids_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
