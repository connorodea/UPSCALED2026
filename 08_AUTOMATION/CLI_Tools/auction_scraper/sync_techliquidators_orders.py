#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scrape_auctions import USER_AGENT


DEFAULT_ORDER_URLS = [
    "https://www.techliquidators.com/orders/",
    "https://www.techliquidators.com/orders",
    "https://www.techliquidators.com/account/orders",
    "https://www.techliquidators.com/account/my-orders",
    "https://www.techliquidators.com/my-orders",
]

PALLET_RE = re.compile(r"\b[A-Z]{3,5}\d{4,}\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync TechLiquidators My Orders.")
    parser.add_argument("--cookie-file", help="Netscape cookie file for TechLiquidators")
    parser.add_argument("--cookie-header", help="Raw Cookie header value")
    parser.add_argument("--orders-url", help="Override orders URL")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages to fetch (0 = all)")
    parser.add_argument("--out-dir", default="upscaled-tl/data/techliquidators")
    parser.add_argument("--save-html", action="store_true", help="Save fetched HTML for debugging")
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
                if not line.strip():
                    continue
                if line.startswith("#") and not line.startswith("#HttpOnly_"):
                    continue
                parts = line.strip().split("\t")
                if len(parts) < 7:
                    continue
                domain, _, path, secure, _, name, value = parts[:7]
                if domain.startswith("#HttpOnly_"):
                    domain = domain[len("#HttpOnly_") :]
                jar.set(name, value, domain=domain, path=path, secure=secure.lower() == "true")
        return jar
    except FileNotFoundError:
        return None


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


def parse_lot_info(text: str) -> Dict[str, Optional[str]]:
    parts = [p.strip() for p in text.split("|") if p.strip()]
    result = {"condition": None, "lot_size": None, "item_count": None}
    if len(parts) >= 1:
        result["condition"] = parts[0]
    if len(parts) >= 2:
        result["lot_size"] = parts[1]
    if len(parts) >= 3:
        result["item_count"] = parts[2]
    return result


def parse_msrp(title: str) -> Optional[float]:
    match = re.search(r"orig\.\s*retail\s*\$([\d,]+)", title, re.IGNORECASE)
    if not match:
        return None
    return parse_currency(match.group(1))


def parse_manifest_links(html: str, base_url: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    manifest_map: Dict[str, str] = {}
    for link in soup.find_all("a", href=True):
        href = link.get("href") or ""
        if not href.endswith("manifest.xlsx"):
            continue
        match = re.search(r"/orders/([A-Z0-9]+)/manifest\.xlsx", href, re.IGNORECASE)
        if not match:
            continue
        order_id = match.group(1).upper()
        manifest_map[order_id] = urljoin(base_url, href)
    return manifest_map


def parse_orders_from_text(text: str) -> List[Dict[str, object]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    orders: List[Dict[str, object]] = []
    i = 0
    while i < len(lines):
        if lines[i].upper() != "DATE":
            i += 1
            continue
        order: Dict[str, object] = {
            "date": lines[i + 1] if i + 1 < len(lines) else "",
            "order_id": "",
            "total": None,
            "ship_to": "",
            "status": "",
            "items": [],
        }
        i += 2
        while i < len(lines) and lines[i].upper() != "DATE":
            label = lines[i].upper()
            if label == "ORDER":
                order["order_id"] = lines[i + 1] if i + 1 < len(lines) else ""
                i += 2
                continue
            if label == "TOTAL":
                order["total"] = parse_currency(lines[i + 1]) if i + 1 < len(lines) else None
                i += 2
                continue
            if label == "SHIPPED TO":
                ship_lines = []
                i += 1
                while i < len(lines) and lines[i].upper() not in {"STATUS", "DATE", "ORDER", "TOTAL"}:
                    ship_lines.append(lines[i])
                    i += 1
                order["ship_to"] = " ".join(ship_lines).strip()
                continue
            if label == "STATUS":
                order["status"] = lines[i + 1] if i + 1 < len(lines) else ""
                i += 2
                continue

            if "orig. retail" in lines[i].lower():
                item = {
                    "title": lines[i],
                    "msrp": parse_msrp(lines[i]),
                    "condition": None,
                    "lot_size": None,
                    "item_count": None,
                    "price": None,
                    "pallet_ids": [],
                }
                i += 1
                while i < len(lines):
                    if lines[i].upper() in {"DATE", "ORDER", "TOTAL", "SHIPPED TO", "STATUS"}:
                        break
                    if "orig. retail" in lines[i].lower():
                        break
                    line = lines[i]
                    if line.startswith("$"):
                        item["price"] = parse_currency(line)
                    if re.search(r"\d+\s*Items", line, re.IGNORECASE):
                        count = parse_int(re.sub(r"[^0-9]", "", line))
                        if count is not None:
                            current = item.get("item_count") or 0
                            if count > current:
                                item["item_count"] = count
                    if "lot" in line.lower() or "pallet" in line.lower():
                        if "items" not in line.lower() and line.strip() != "|":
                            item["lot_size"] = line.strip()
                    if item.get("condition") is None:
                        if any(token in line.lower() for token in ["returns", "working", "new", "damaged", "refurb"]):
                            item["condition"] = line.strip()
                    for match in PALLET_RE.findall(line):
                        if match not in item["pallet_ids"]:
                            item["pallet_ids"].append(match)
                    i += 1
                order["items"].append(item)
                continue
            i += 1

        if order["order_id"] or order["items"]:
            orders.append(order)
    return orders


def find_next_page(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        text = a_tag.get_text(" ", strip=True).lower()
        if text in {"next", "next page"} or "next" in a_tag.get("aria-label", "").lower():
            href = a_tag["href"]
            return urljoin(base_url, href)
    return None


def fetch_pages(session: requests.Session, start_url: str, max_pages: int) -> List[Dict[str, str]]:
    pages = []
    url = start_url
    seen = set()
    while url and url not in seen:
        seen.add(url)
        resp = session.get(url, timeout=30, allow_redirects=True)
        if resp.status_code != 200:
            break
        if "/login" in resp.url or "/sign_in" in resp.url:
            break
        pages.append({"url": resp.url, "html": resp.text})
        if max_pages and len(pages) >= max_pages:
            break
        url = find_next_page(resp.text, resp.url)
    return pages


def main() -> int:
    args = parse_args()
    out_dir = resolve_path(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    if args.cookie_header:
        session.headers.update({"Cookie": args.cookie_header})
    elif args.cookie_file:
        jar = load_cookie_jar(args.cookie_file)
        if jar:
            session.cookies = jar

    base_url = args.orders_url or DEFAULT_ORDER_URLS[0]
    pages = fetch_pages(session, base_url, args.max_pages)
    if not pages:
        if not args.orders_url:
            for fallback in DEFAULT_ORDER_URLS[1:]:
                pages = fetch_pages(session, fallback, args.max_pages)
                if pages:
                    break

    if not pages:
        print("No orders pages fetched. Check login/cookies or provide --orders-url.")
        return 1

    all_orders: List[Dict[str, object]] = []
    manifest_lookup: Dict[str, str] = {}
    for page in pages:
        soup = BeautifulSoup(page["html"], "html.parser")
        text = soup.get_text("\n", strip=True)
        orders = parse_orders_from_text(text)
        all_orders.extend(orders)
        manifest_lookup.update(parse_manifest_links(page["html"], page["url"]))

    for order in all_orders:
        order_id = str(order.get("order_id", "")).strip().upper()
        if order_id and order_id in manifest_lookup:
            order["manifest_url"] = manifest_lookup[order_id]

    payload = {
        "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
        "source_urls": [p["url"] for p in pages],
        "orders": all_orders,
    }
    with open(os.path.join(out_dir, "orders.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True)

    if args.save_html:
        for idx, page in enumerate(pages, start=1):
            with open(os.path.join(out_dir, f"orders_page_{idx}.html"), "w", encoding="utf-8") as f:
                f.write(page["html"])

    print(f"Wrote {len(all_orders)} orders to {os.path.join(out_dir, 'orders.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
