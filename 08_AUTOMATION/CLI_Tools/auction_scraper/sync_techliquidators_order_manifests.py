#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from scrape_auctions import USER_AGENT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download TechLiquidators order manifest files."
    )
    parser.add_argument("--cookie-file", help="Netscape cookie file for TechLiquidators")
    parser.add_argument("--cookie-header", help="Raw Cookie header value")
    parser.add_argument(
        "--orders-file",
        default="upscaled-tl/data/techliquidators/orders.json",
        help="Orders JSON file",
    )
    parser.add_argument(
        "--out-dir",
        default="upscaled-tl/data/techliquidators/order_manifests",
        help="Output directory for order manifests",
    )
    parser.add_argument("--year-min", type=int, default=2025)
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


def parse_order_year(value: str) -> int:
    if not value:
        return 0
    try:
        return int(value.strip()[-4:])
    except ValueError:
        return 0


def main() -> int:
    args = parse_args()
    orders_path = Path(resolve_path(args.orders_file))
    out_dir = Path(resolve_path(args.out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    if not orders_path.exists():
        print(f"Orders file not found: {orders_path}")
        return 1

    data = json.loads(orders_path.read_text(encoding="utf-8"))
    orders = data.get("orders") or []

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    if args.cookie_header:
        session.headers.update({"Cookie": args.cookie_header})
    elif args.cookie_file:
        jar = load_cookie_jar(args.cookie_file)
        if jar:
            session.cookies = jar

    downloaded = 0
    skipped = 0
    for order in orders:
        order_id = str(order.get("order_id", "")).strip().upper()
        order_date = str(order.get("date", "")).strip()
        if not order_id or parse_order_year(order_date) < args.year_min:
            continue
        manifest_url = str(order.get("manifest_url", "")).strip()
        if not manifest_url:
            continue
        parsed = urlparse(manifest_url)
        filename = f"order_manifest_{order_id}.xlsx"
        out_path = out_dir / filename
        if out_path.exists():
            skipped += 1
            continue
        resp = session.get(manifest_url, timeout=60)
        if resp.status_code != 200 or "/login" in resp.url or "/sign_in" in resp.url:
            continue
        out_path.write_bytes(resp.content)
        downloaded += 1

    print(f"Downloaded {downloaded} manifests, skipped {skipped} existing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
