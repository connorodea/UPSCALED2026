#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

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

CURRENCY_RE = re.compile(r"\$\s*([0-9,]+(?:\.[0-9]{2})?)")
INT_RE = re.compile(r"\b([0-9,]+)\b")
WHITESPACE_RE = re.compile(r"\s+")
WEIGHT_RE = re.compile(r"([0-9,]+(?:\.[0-9]+)?)\s*lb", re.I)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def extract_auction_id(url: str) -> Optional[str]:
    match = re.search(r"/(ml\d+)/", url)
    if match:
        return match.group(1)
    return None


def fetch_html(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.text


def download_file(url: str, path: str) -> None:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)


def get_meta_content(soup: BeautifulSoup, key: str, attr: str = "property") -> Optional[str]:
    tag = soup.find("meta", attrs={attr: key})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def parse_kv_pairs(soup: BeautifulSoup) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []

    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        if dts and dds and len(dts) == len(dds):
            for dt_el, dd_el in zip(dts, dds):
                label = " ".join(dt_el.get_text(" ", strip=True).split())
                value = " ".join(dd_el.get_text(" ", strip=True).split())
                if label and value:
                    pairs.append((label, value))

    for li in soup.find_all("li"):
        text = " ".join(li.get_text(" ", strip=True).split())
        if ":" in text:
            label, value = text.split(":", 1)
            label = label.strip()
            value = value.strip()
            if label and value:
                pairs.append((label, value))

    for label_el in soup.find_all(class_=re.compile(r"label", re.I)):
        value_el = label_el.find_next_sibling()
        if not value_el:
            continue
        label = " ".join(label_el.get_text(" ", strip=True).split())
        value = " ".join(value_el.get_text(" ", strip=True).split())
        if label and value:
            pairs.append((label, value))

    return pairs


def normalize_label(label: str) -> str:
    return WHITESPACE_RE.sub(" ", label.strip().lower())


def should_keep_pair(label: str, value: str) -> bool:
    if not label or not value:
        return False
    if "?" in label:
        return False
    if "{{" in label or "}}" in label:
        return False
    if len(label) > 48:
        return False
    return True


def filter_pairs(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return [(label, value) for label, value in pairs if should_keep_pair(label, value)]


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


def dedupe_preserve(values: List[str]) -> List[str]:
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


def normalize_pairs(pairs: List[Tuple[str, str]]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for label, value in pairs:
        key = LABEL_MAP.get(normalize_label(label))
        if key and key not in normalized:
            normalized[key] = value
    return normalized


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
        rows.append(
            {
                "customer": cells[0],
                "bid": cells[1],
                "date": cells[2],
            }
        )
    return rows


def parse_page(html: str, url: str) -> Dict[str, object]:
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

    if listing_title and not description and " - " in listing_title:
        description = listing_title

    ld_json_payloads = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        ld_json_payloads.append(payload)

    if ld_json_payloads and not title:
        for payload in ld_json_payloads:
            if isinstance(payload, dict) and payload.get("name"):
                title = payload.get("name")
                break
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and item.get("name"):
                        title = item.get("name")
                        break
                if title:
                    break

    if ld_json_payloads and not description:
        for payload in ld_json_payloads:
            if isinstance(payload, dict) and payload.get("description"):
                description = payload.get("description")
                break
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and item.get("description"):
                        description = item.get("description")
                        break
                if description:
                    break

    if ld_json_payloads and not images:
        for payload in ld_json_payloads:
            if isinstance(payload, dict) and payload.get("image"):
                image = payload.get("image")
                images.extend(image if isinstance(image, list) else [image])
                break
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and item.get("image"):
                        image = item.get("image")
                        images.extend(image if isinstance(image, list) else [image])
                        break
                if images:
                    break

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
        "auction_id": extract_auction_id(url),
        "slug": slugify(url.split("/")[-2]) if url.rstrip("/").split("/")[-1] else slugify(url.split("/")[-3]),
        "title": title,
        "description": description,
        "images": dedupe_preserve(images),
        "raw_kv_pairs": [{"label": k, "value": v} for k, v in pairs],
        "kv_pairs": [{"label": k, "value": v} for k, v in filtered_pairs],
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
        latest_bid = bid_history[0]
        result["latest_bid"] = latest_bid

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


def build_output_dir(base_dir: str, year: str, folder_name: Optional[str], auction_id: Optional[str], slug: str) -> str:
    if folder_name:
        return os.path.join(base_dir, year, folder_name)

    parts = ["TL"]
    if auction_id:
        parts.append(auction_id)
    if slug:
        parts.append(slug)
    name = "_".join(parts)
    return os.path.join(base_dir, year, name)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and normalize TechLiquidators auction data."
    )
    parser.add_argument("--url", required=True, help="TechLiquidators auction URL")
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
        "--folder-name",
        help="Optional folder name override (default: TL_<auction_id>_<slug>)",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Only save raw HTML, skip parsing",
    )
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Download the manifest XLSX when available",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = args.url.strip()

    html = fetch_html(url)
    extracted_at = dt.datetime.now(dt.timezone.utc).isoformat()

    auction_id = extract_auction_id(url)
    slug = slugify(url.rstrip("/").split("/")[-1])
    out_base = resolve_out_base(args.out_base)
    out_dir = build_output_dir(out_base, args.year, args.folder_name, auction_id, slug)
    os.makedirs(out_dir, exist_ok=True)

    raw_path = os.path.join(out_dir, "raw.html")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(html)

    if not args.raw_only:
        data = parse_page(html, url)
        data["extracted_at"] = extracted_at
        data["output_dir"] = os.path.abspath(out_dir)
        json_path = os.path.join(out_dir, "auction.json")
        csv_path = os.path.join(out_dir, "auction.csv")
        write_json(json_path, data)
        write_csv(csv_path, data)

        if args.manifest and data.get("manifest_url"):
            manifest_path = os.path.join(out_dir, "manifest.xlsx")
            download_file(str(data["manifest_url"]), manifest_path)

    print(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
