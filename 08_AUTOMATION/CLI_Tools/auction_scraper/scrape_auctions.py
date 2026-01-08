#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from collections import deque
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from typing import Callable, Dict, Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

CURRENCY_RE = re.compile(r"\$\s*([0-9,]+(?:\.[0-9]{2})?)")
INT_RE = re.compile(r"\b([0-9,]+)\b")
WEIGHT_RE = re.compile(r"([0-9,]+(?:\.[0-9]+)?)\s*lb", re.I)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class SiteConfig:
    name: str
    start_urls: List[str]
    detail_patterns: List[re.Pattern]
    pagination_patterns: List[re.Pattern]
    parse_detail: Callable[[str, str], Dict[str, object]]


LABEL_MAP = {
    "lot #": "lot_number",
    "lot number": "lot_number",
    "auction id": "auction_id",
    "condition": "condition",
    "location": "location",
    "est. msrp": "msrp",
    "msrp": "msrp",
    "retail value": "retail_value",
    "quantity": "quantity",
    "units": "quantity",
    "pallet count": "pallet_count",
    "buyer premium": "buyer_premium",
    "auction ends": "auction_end",
    "auction end": "auction_end",
    "bidding ends": "auction_end",
    "bidding starts": "auction_start",
    "start time": "auction_start",
    "end time": "auction_end",
    "current bid": "current_bid",
    "reserve": "reserve",
    "seller": "seller",
    "manifest": "manifest",
    "lot id": "lot_id",
    "total items": "total_items",
    "weight": "weight",
}


SUMMARY_FIELDS = [
    "site",
    "url",
    "title",
    "auction_id",
    "lot_id",
    "lot_number",
    "current_bid_value",
    "lot_price_value",
    "msrp_value",
    "retail_value_value",
    "items_count_value",
    "total_items_value",
    "condition",
    "warehouse",
    "location",
    "auction_end",
    "manifest_url",
]


TECHLIQUIDATORS_PATTERN = re.compile(r"/detail/[^/]+/[^/?#]+", re.I)
LIQUIDATION_DETAIL_PATTERN = re.compile(r"/auction/\d+|/p/\d+|/lot/\d+", re.I)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def parse_currency(value: str) -> Optional[float]:
    match = CURRENCY_RE.search(value)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def parse_int(value: str) -> Optional[int]:
    match = INT_RE.search(value.replace(",", ""))
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_weight_lbs(value: str) -> Optional[float]:
    match = WEIGHT_RE.search(value)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def normalize_label(label: str) -> str:
    return WHITESPACE_RE.sub(" ", label.strip().lower())


def dedupe_preserve(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in values:
        if not item:
            continue
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def parse_kv_pairs(soup: BeautifulSoup) -> List[Dict[str, str]]:
    pairs: List[Dict[str, str]] = []

    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        if dts and dds and len(dts) == len(dds):
            for dt_el, dd_el in zip(dts, dds):
                label = " ".join(dt_el.get_text(" ", strip=True).split())
                value = " ".join(dd_el.get_text(" ", strip=True).split())
                if label and value:
                    pairs.append({"label": label, "value": value})

    for li in soup.find_all("li"):
        text = " ".join(li.get_text(" ", strip=True).split())
        if ":" in text:
            label, value = text.split(":", 1)
            label = label.strip()
            value = value.strip()
            if label and value:
                pairs.append({"label": label, "value": value})

    return pairs


def filter_pairs(pairs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    filtered = []
    for pair in pairs:
        label = pair.get("label", "")
        value = pair.get("value", "")
        if not label or not value:
            continue
        if "?" in label or "{{" in label or "}}" in label:
            continue
        if len(label) > 48:
            continue
        filtered.append(pair)
    return filtered


def normalize_pairs(pairs: List[Dict[str, str]]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for pair in pairs:
        key = LABEL_MAP.get(normalize_label(pair["label"]))
        if key and key not in normalized:
            normalized[key] = pair["value"]
    return normalized


def get_meta_content(soup: BeautifulSoup, key: str, attr: str = "property") -> Optional[str]:
    tag = soup.find("meta", attrs={attr: key})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def parse_ld_json(soup: BeautifulSoup) -> List[object]:
    payloads = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        payloads.append(payload)
    return payloads


def parse_listing_title(soup: BeautifulSoup) -> Optional[str]:
    title_node = soup.find(attrs={"edit-listing-title": "true"})
    if title_node and title_node.get("title"):
        return title_node["title"].strip()
    return None


def parse_outline_fields(soup: BeautifulSoup) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for box in soup.select(".listing-outline-box"):
        for item in box.select(".spacing-bottom"):
            strong = item.find("strong")
            if not strong:
                continue
            label = normalize_label(strong.get_text(" ", strip=True).rstrip(":"))
            value_text = item.get_text(" ", strip=True)
            value = value_text.replace(strong.get_text(" ", strip=True), "").strip()
            if label and value:
                result[label] = value
    return result


def parse_pricing_box_attrs(soup: BeautifulSoup) -> Dict[str, str]:
    node = soup.find(attrs={"lot-pricing-box": "true"})
    if not node:
        return {}
    attrs = {}
    for key in [
        "items-count",
        "subtotal-cents",
        "default-shipping-cents",
        "shipping-method",
        "bid-count",
        "current-bid",
        "listing-name",
    ]:
        if node.has_attr(key):
            attrs[key] = node.get(key)
    return attrs


def parse_bid_history(soup: BeautifulSoup) -> List[Dict[str, str]]:
    rows = []
    table = soup.select_one("#bid-history-modal-dialog table")
    if not table:
        return rows
    for row in table.select("tbody tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) != 3:
            continue
        rows.append({"customer": cells[0], "bid": cells[1], "date": cells[2]})
    return rows


def parse_techliquidators_detail(html: str, url: str) -> Dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")

    listing_title = parse_listing_title(soup)
    title = listing_title or get_meta_content(soup, "og:title") or (
        soup.find("h1").get_text(strip=True) if soup.find("h1") else None
    )
    description = get_meta_content(soup, "og:description")

    images = []
    for tag in soup.find_all("meta", attrs={"property": "og:image"}):
        if tag.get("content"):
            images.append(tag["content"].strip())
    if not images:
        og_image = get_meta_content(soup, "og:image")
        if og_image:
            images.append(og_image)
    for img in soup.select("img.listing-images__thumb, img.listing-images__image"):
        src = img.get("src")
        if src:
            images.append(src.strip())

    pairs = parse_kv_pairs(soup)
    filtered_pairs = filter_pairs(pairs)
    normalized = normalize_pairs(filtered_pairs)

    outline_fields = parse_outline_fields(soup)
    pricing_attrs = parse_pricing_box_attrs(soup)
    bid_history = parse_bid_history(soup)

    manifest_url = None
    manifest_link = soup.select_one("a.listing-details__download-manifest-link")
    if manifest_link and manifest_link.get("href"):
        manifest_url = urljoin(url, manifest_link["href"])

    ld_json_payloads = parse_ld_json(soup)
    if ld_json_payloads:
        for payload in ld_json_payloads:
            if isinstance(payload, dict):
                ld_name = payload.get("name")
                ld_description = payload.get("description")
            else:
                ld_name = None
                ld_description = None
                if isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict) and (item.get("name") or item.get("description")):
                            ld_name = ld_name or item.get("name")
                            ld_description = ld_description or item.get("description")
            if ld_name and title and title.lower().startswith("techliquidators"):
                title = ld_name
            if ld_description and description and description.lower().startswith("source discounted"):
                description = ld_description
            if ld_description and not description:
                description = ld_description

    result: Dict[str, object] = {
        "url": url,
        "site": "techliquidators",
        "auction_id": extract_techliquidators_id(url),
        "title": title,
        "description": description,
        "images": dedupe_preserve(images),
        "raw_kv_pairs": pairs,
        "kv_pairs": filtered_pairs,
        "manifest_url": manifest_url,
        "outline_fields": outline_fields,
        "pricing_attrs": pricing_attrs,
        "bid_history": bid_history,
        "ld_json": ld_json_payloads,
    }

    for key, value in normalized.items():
        result[key] = value

    if "condition" not in result and outline_fields.get("condition"):
        result["condition"] = outline_fields.get("condition")
    if "warehouse" not in result and outline_fields.get("warehouse"):
        result["warehouse"] = outline_fields.get("warehouse")
    if outline_fields.get("lot size"):
        result["lot_size"] = outline_fields.get("lot size")

    if pricing_attrs:
        if pricing_attrs.get("listing-name"):
            result["lot_id"] = pricing_attrs.get("listing-name")
        if pricing_attrs.get("items-count"):
            result["items_count"] = pricing_attrs.get("items-count")
        if pricing_attrs.get("bid-count"):
            result["bid_count"] = pricing_attrs.get("bid-count")
        if pricing_attrs.get("shipping-method"):
            result["shipping_method"] = pricing_attrs.get("shipping-method")
        if pricing_attrs.get("subtotal-cents"):
            result["subtotal_cents"] = pricing_attrs.get("subtotal-cents")
        if pricing_attrs.get("default-shipping-cents"):
            result["default_shipping_cents"] = pricing_attrs.get("default-shipping-cents")

    if bid_history:
        result["latest_bid"] = bid_history[0]

    result["msrp_value"] = parse_currency(str(result.get("msrp", "")))
    result["retail_value_value"] = parse_currency(str(result.get("retail_value", "")))
    result["current_bid_value"] = parse_currency(str(result.get("current_bid", "")))
    result["buyer_premium_value"] = parse_currency(str(result.get("buyer_premium", "")))
    result["quantity_value"] = parse_int(str(result.get("quantity", "")))
    result["pallet_count_value"] = parse_int(str(result.get("pallet_count", "")))

    if listing_title and "orig. retail" in listing_title.lower():
        result["orig_retail"] = listing_title
        result["orig_retail_value"] = parse_currency(listing_title)
        if not result.get("msrp_value"):
            result["msrp_value"] = result.get("orig_retail_value")
        if not result.get("retail_value_value"):
            result["retail_value_value"] = result.get("orig_retail_value")

    if result.get("weight"):
        weight_lbs = parse_weight_lbs(str(result.get("weight")))
        if weight_lbs is not None:
            result["weight_lbs"] = weight_lbs

    if result.get("total_items"):
        total_items_value = parse_int(str(result.get("total_items")))
        if total_items_value is not None:
            result["total_items_value"] = total_items_value

    if result.get("subtotal_cents"):
        try:
            result["lot_price_value"] = float(result["subtotal_cents"]) / 100
        except ValueError:
            pass
    if result.get("default_shipping_cents"):
        try:
            result["default_shipping_value"] = float(result["default_shipping_cents"]) / 100
        except ValueError:
            pass

    if result.get("items_count"):
        parsed_items = parse_int(str(result.get("items_count")))
        if parsed_items is not None:
            result["items_count_value"] = parsed_items

    if result.get("bid_history"):
        bid_values = [
            parse_currency(entry.get("bid", ""))
            for entry in result["bid_history"]
            if isinstance(entry, dict)
        ]
        bid_values = [value for value in bid_values if value is not None]
        if bid_values and not result.get("current_bid_value"):
            result["current_bid_value"] = bid_values[0]

    return result


def parse_liquidation_detail(html: str, url: str) -> Dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")

    title = get_meta_content(soup, "og:title") or (
        soup.find("h1").get_text(strip=True) if soup.find("h1") else None
    )
    description = get_meta_content(soup, "og:description")

    images = []
    for tag in soup.find_all("meta", attrs={"property": "og:image"}):
        if tag.get("content"):
            images.append(tag["content"].strip())
    for img in soup.find_all("img"):
        if img.get("src") and "http" in img.get("src"):
            images.append(img.get("src"))

    pairs = parse_kv_pairs(soup)
    filtered_pairs = filter_pairs(pairs)
    normalized = normalize_pairs(filtered_pairs)

    ld_json_payloads = parse_ld_json(soup)
    if ld_json_payloads:
        for payload in ld_json_payloads:
            if isinstance(payload, dict):
                if payload.get("name") and not title:
                    title = payload.get("name")
                if payload.get("description") and not description:
                    description = payload.get("description")

    manifest_url = None
    for link in soup.find_all("a", href=True):
        href = link["href"].lower()
        if "manifest" in href or href.endswith(".xlsx") or href.endswith(".csv"):
            manifest_url = urljoin(url, link["href"])
            break

    result: Dict[str, object] = {
        "url": url,
        "site": "liquidation",
        "title": title,
        "description": description,
        "images": dedupe_preserve(images),
        "raw_kv_pairs": pairs,
        "kv_pairs": filtered_pairs,
        "manifest_url": manifest_url,
        "ld_json": ld_json_payloads,
    }

    for key, value in normalized.items():
        result[key] = value

    result["msrp_value"] = parse_currency(str(result.get("msrp", "")))
    result["retail_value_value"] = parse_currency(str(result.get("retail_value", "")))
    result["current_bid_value"] = parse_currency(str(result.get("current_bid", "")))
    result["quantity_value"] = parse_int(str(result.get("quantity", "")))
    result["pallet_count_value"] = parse_int(str(result.get("pallet_count", "")))

    if result.get("weight"):
        weight_lbs = parse_weight_lbs(str(result.get("weight")))
        if weight_lbs is not None:
            result["weight_lbs"] = weight_lbs

    return result


def extract_techliquidators_id(url: str) -> Optional[str]:
    match = re.search(r"/detail/([^/]+)/", url, re.I)
    if match:
        return match.group(1).lower()
    return None


def extract_liquidation_id(url: str) -> Optional[str]:
    match = re.search(r"/(auction|p|lot)/(\d+)", url, re.I)
    if match:
        return match.group(2)
    return None


def fetch_response(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response


def fetch(session: requests.Session, url: str) -> str:
    return fetch_response(session, url).text


def download_file(session: requests.Session, url: str, path: str) -> None:
    response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)


def is_same_host(base_url: str, target_url: str) -> bool:
    return urlparse(base_url).netloc == urlparse(target_url).netloc


def collect_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#"):
            continue
        abs_url = urljoin(base_url, href)
        if is_same_host(base_url, abs_url):
            links.append(abs_url)
    return links


def extract_links_from_html(html: str, base_url: str) -> List[str]:
    links = set()
    for match in re.findall(r"/detail/[a-z0-9\\-_/]+", html, re.I):
        links.add(urljoin(base_url, match))
    for match in re.findall(r"/c/FergusonHome[^\"'\\s>]+", html, re.I):
        links.add(urljoin(base_url, match))
    for match in re.findall(r"[?&]page=\\d+", html, re.I):
        base = base_url.split("?")[0]
        links.add(base + match)
    return list(links)


def find_detail_links(links: Iterable[str], patterns: List[re.Pattern]) -> List[str]:
    result = []
    for link in links:
        for pattern in patterns:
            if pattern.search(link):
                result.append(link)
                break
    return result


def find_pagination_links(links: Iterable[str], patterns: List[re.Pattern]) -> List[str]:
    result = []
    for link in links:
        for pattern in patterns:
            if pattern.search(link):
                result.append(link)
                break
    return result


def build_output_dir(base_dir: str, site: str, year: str, item_id: Optional[str], slug: str) -> str:
    parts = [site]
    if item_id:
        parts.append(item_id)
    if slug:
        parts.append(slug)
    folder_name = "_".join(parts)
    return os.path.join(base_dir, site, year, folder_name)


def find_project_root(start: str) -> Optional[str]:
    current = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(current, "01_SOURCING")) and os.path.isdir(
            os.path.join(current, "08_AUTOMATION")
        ):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def resolve_out_base(out_base: str) -> str:
    if os.path.isabs(out_base):
        return out_base

    root = find_project_root(os.getcwd()) or find_project_root(os.path.dirname(__file__))
    if root:
        return os.path.join(root, out_base)

    return out_base


def write_json(path: str, data: Dict[str, object]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def write_csv(path: str, data: Dict[str, object]) -> None:
    flat = {}
    for key, value in data.items():
        if isinstance(value, list):
            flat[key] = "; ".join(str(item) for item in value)
        elif isinstance(value, dict):
            flat[key] = json.dumps(value)
        else:
            flat[key] = "" if value is None else value

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(flat.keys()))
        writer.writeheader()
        writer.writerow(flat)


def append_jsonl(path: str, entry: Dict[str, object]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True))
        f.write("\n")


def load_jsonl(path: str) -> List[Dict[str, object]]:
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def write_summary_csv(path: str, entries: List[Dict[str, object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for entry in entries:
            row = {field: entry.get(field, "") for field in SUMMARY_FIELDS}
            writer.writerow(row)


def append_log(path: str, message: str) -> None:
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def crawl_listing_pages(
    session: requests.Session,
    config: SiteConfig,
    max_pages: Optional[int],
    delay: float,
    log_path: str,
) -> List[str]:
    queue = deque(config.start_urls)
    visited: Set[str] = set()
    detail_urls: List[str] = []

    while queue:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        if max_pages and len(visited) > max_pages:
            break

        try:
            html = fetch(session, url)
        except requests.RequestException as exc:
            append_log(log_path, f"listing_fetch_failed url={url} error={exc}")
            continue
        soup = BeautifulSoup(html, "html.parser")
        links = collect_links(soup, url)
        links.extend(extract_links_from_html(html, url))

        detail_urls.extend(find_detail_links(links, config.detail_patterns))
        queue.extend(find_pagination_links(links, config.pagination_patterns))

        if delay:
            time.sleep(delay)

    return dedupe_preserve(detail_urls)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape TechLiquidators and Liquidation.com auctions.")
    parser.add_argument(
        "--site",
        required=True,
        choices=["techliquidators", "liquidation"],
        help="Site to scrape",
    )
    parser.add_argument(
        "--out-base",
        default="01_SOURCING/Auctions",
        help="Base output directory (default: 01_SOURCING/Auctions)",
    )
    parser.add_argument(
        "--year",
        default=str(dt.datetime.now().year),
        help="Output year directory (default: current year)",
    )
    parser.add_argument(
        "--start-url",
        action="append",
        help="Override start URL(s). Can be used multiple times.",
    )
    parser.add_argument("--max-pages", type=int, help="Max listing pages to crawl")
    parser.add_argument("--max-auctions", type=int, help="Max auction detail pages to scrape")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--manifest", action="store_true", help="Download manifest files when available")
    parser.add_argument("--resume", action="store_true", help="Skip auctions already downloaded")
    parser.add_argument("--cookie-file", help="Path to Netscape-format cookie jar file")
    parser.add_argument("--cookie-header", help="Raw Cookie header value to include in requests")
    parser.add_argument(
        "--header",
        action="append",
        help="Additional request header in the form 'Key: Value' (repeatable)",
    )
    return parser.parse_args()


def build_config(site: str, start_urls: Optional[List[str]]) -> SiteConfig:
    if site == "techliquidators":
        default_start = ["https://www.techliquidators.com/lots/?auction=true"]
        return SiteConfig(
            name=site,
            start_urls=start_urls or default_start,
            detail_patterns=[TECHLIQUIDATORS_PATTERN],
            pagination_patterns=[re.compile(r"/lots/\?"), re.compile(r"page=")],
            parse_detail=parse_techliquidators_detail,
        )

    default_start = ["https://www.liquidation.com/c/FergusonHome"]
    return SiteConfig(
        name=site,
        start_urls=start_urls or default_start,
        detail_patterns=[LIQUIDATION_DETAIL_PATTERN],
        pagination_patterns=[re.compile(r"/c/FergusonHome"), re.compile(r"page=")],
        parse_detail=parse_liquidation_detail,
    )


def main() -> int:
    args = parse_args()
    config = build_config(args.site, args.start_url)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    if args.cookie_header:
        session.headers.update({"Cookie": args.cookie_header})
    if args.header:
        for header in args.header:
            if ":" not in header:
                continue
            key, value = header.split(":", 1)
            session.headers.update({key.strip(): value.strip()})
    if args.cookie_file:
        jar = MozillaCookieJar()
        try:
            jar.load(args.cookie_file, ignore_discard=True, ignore_expires=True)
            session.cookies.update(jar)
        except OSError:
            pass

    out_base = resolve_out_base(args.out_base)
    site_root = os.path.join(out_base, config.name, args.year)
    os.makedirs(site_root, exist_ok=True)
    log_path = os.path.join(site_root, "scrape.log")

    detail_urls = crawl_listing_pages(session, config, args.max_pages, args.delay, log_path)
    if args.max_auctions:
        detail_urls = detail_urls[: args.max_auctions]

    index_path = os.path.join(site_root, "index.jsonl")
    summary_path = os.path.join(site_root, "index.csv")

    existing_entries = load_jsonl(index_path)
    existing_urls = {entry.get("url") for entry in existing_entries if entry.get("url")}

    new_entries = []

    for url in detail_urls:
        if args.resume and url in existing_urls:
            continue

        try:
            response = fetch_response(session, url)
        except requests.RequestException as exc:
            append_log(log_path, f"detail_fetch_failed url={url} error={exc}")
            continue
        html = response.text
        final_url = response.url
        data = config.parse_detail(html, final_url)
        data["extracted_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

        item_id = None
        if config.name == "techliquidators":
            item_id = data.get("auction_id") or extract_techliquidators_id(final_url)
        else:
            item_id = extract_liquidation_id(final_url)

        slug = slugify(data.get("title") or final_url.split("/")[-1])
        out_dir = build_output_dir(out_base, config.name, args.year, item_id, slug)
        os.makedirs(out_dir, exist_ok=True)

        raw_path = os.path.join(out_dir, "raw.html")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(html)

        json_path = os.path.join(out_dir, "auction.json")
        csv_path = os.path.join(out_dir, "auction.csv")

        data["output_dir"] = os.path.abspath(out_dir)
        write_json(json_path, data)
        write_csv(csv_path, data)

        if args.manifest and data.get("manifest_url"):
            manifest_path = os.path.join(out_dir, "manifest.xlsx")
            try:
                download_file(session, str(data["manifest_url"]), manifest_path)
            except requests.RequestException:
                append_log(log_path, f"manifest_download_failed url={data.get('manifest_url')}")

        append_jsonl(index_path, data)
        existing_urls.add(url)
        new_entries.append(data)

        if args.delay:
            time.sleep(args.delay)

    combined_entries = existing_entries + new_entries
    write_summary_csv(summary_path, combined_entries)

    print(site_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
