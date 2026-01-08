#!/usr/bin/env python3
"""
Scrape real product images from Samsung and retailer websites
Uses web scraping to find actual, valid image URLs
"""

import requests
import os
import csv
import time
import json
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from ebay_trading_uploader import EbayTradingAPI

load_dotenv()


def search_amazon_images(model: str) -> list:
    """Search Amazon for product images"""
    try:
        # Amazon search URL
        search_query = f"Samsung {model}".replace(' ', '+')
        url = f"https://www.amazon.com/s?k={search_query}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find product images
        images = []
        for img in soup.find_all('img', {'class': 's-image'}):
            src = img.get('src')
            if src and 'jpg' in src and 'https://' in src:
                # Get high-res version
                src = re.sub(r'_AC_.*?_', '_AC_SL1500_', src)
                images.append(src)
                if len(images) >= 3:
                    break

        return images
    except Exception as e:
        return []


def search_best_buy_images(model: str) -> list:
    """Search Best Buy for product images"""
    try:
        search_query = f"Samsung {model}".replace(' ', '+')
        url = f"https://www.bestbuy.com/site/searchpage.jsp?st={search_query}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        images = []
        for img in soup.find_all('img', {'class': 'product-image'}):
            src = img.get('src')
            if src and src.startswith('https://'):
                images.append(src)
                if len(images) >= 3:
                    break

        return images
    except Exception as e:
        return []


def get_ebay_stock_images(model: str) -> list:
    """
    Search eBay completed listings for stock photos
    This finds real product images from other sellers
    """
    try:
        search_query = f"Samsung {model}".replace(' ', '%20')
        url = f"https://www.ebay.com/sch/i.html?_nkw={search_query}&LH_Complete=1&LH_Sold=1"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        images = []
        for img in soup.find_all('img', {'class': 's-item__image-img'}):
            src = img.get('src')
            if src and src.startswith('https://') and 'jpg' in src:
                # Get larger version
                src = src.replace('s-l140', 's-l500')
                images.append(src)
                if len(images) >= 3:
                    break

        return images
    except Exception as e:
        return []


def find_valid_images(brand: str, model: str) -> list:
    """
    Try multiple sources to find valid product images
    """
    all_images = []

    print(f"    Searching Amazon...")
    images = search_amazon_images(model)
    if images:
        print(f"    Found {len(images)} on Amazon")
        all_images.extend(images)

    if len(all_images) < 3:
        print(f"    Searching Best Buy...")
        images = search_best_buy_images(model)
        if images:
            print(f"    Found {len(images)} on Best Buy")
            all_images.extend(images)

    if len(all_images) < 3:
        print(f"    Searching eBay sold listings...")
        images = get_ebay_stock_images(model)
        if images:
            print(f"    Found {len(images)} on eBay")
            all_images.extend(images)

    # Validate and deduplicate
    valid_images = []
    seen = set()

    for img_url in all_images[:6]:  # Check top 6
        if img_url in seen:
            continue
        seen.add(img_url)

        try:
            # Quick validation
            resp = requests.head(img_url, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                valid_images.append(img_url)
                if len(valid_images) >= 3:
                    break
        except:
            continue

    return valid_images


def update_listing_images(api: EbayTradingAPI, item_id: str, image_urls: list) -> bool:
    """Update eBay listing with product images"""

    if not image_urls:
        return False

    picture_urls = '\n'.join([f'            <PictureURL>{url}</PictureURL>' for url in image_urls[:12]])

    xml_request = f'''<?xml version="1.0" encoding="utf-8"?>
<ReviseFixedPriceItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{api.auth_token}</eBayAuthToken>
    </RequesterCredentials>
    <Item>
        <ItemID>{item_id}</ItemID>
        <PictureDetails>
            <GalleryType>Gallery</GalleryType>
{picture_urls}
        </PictureDetails>
    </Item>
</ReviseFixedPriceItemRequest>'''

    try:
        response = api._make_xml_request('ReviseFixedPriceItem', xml_request)
        if response.get('Ack') in ['Success', 'Warning']:
            return True
        else:
            errors = response.get('Errors', [])
            if errors:
                print(f"    Error: {errors[0].get('LongMessage', 'Unknown')}")
            return False
    except Exception as e:
        print(f"    Exception: {e}")
        return False


def main():
    dev_id = os.getenv('EBAY_DEV_ID')
    app_id = os.getenv('EBAY_CLIENT_ID')
    cert_id = os.getenv('EBAY_CLIENT_SECRET')
    auth_token = os.getenv('EBAY_AUTH_TOKEN')
    sandbox = os.getenv('EBAY_SANDBOX', 'false').lower() == 'true'

    api = EbayTradingAPI(dev_id, app_id, cert_id, auth_token, sandbox)

    mapping_file = 'item_mapping.csv'
    with open(mapping_file, 'r') as f:
        items = list(csv.DictReader(f))

    print(f"Processing {len(items)} items...")
    print("="*80)

    model_cache = {}
    updated = 0
    failed = 0

    for idx, item in enumerate(items, 1):
        sku = item['sku']
        item_id = item['item_id']
        brand = item['brand'].strip()
        model = item['model'].strip()

        if not model:
            print(f"\n[{idx}/{len(items)}] Skipping - no model")
            failed += 1
            continue

        print(f"\n[{idx}/{len(items)}] {brand} {model}")
        print(f"  Item ID: {item_id}")

        cache_key = model.upper()
        if cache_key in model_cache:
            print(f"  Using cached images")
            images = model_cache[cache_key]
        else:
            print(f"  Searching for images...")
            images = find_valid_images(brand, model)
            model_cache[cache_key] = images
            time.sleep(2)  # Be nice to servers

        if not images:
            print(f"  ✗ No valid images found")
            failed += 1
            continue

        print(f"  ✓ Found {len(images)} valid images")
        for img in images:
            print(f"    - {img[:80]}...")

        print(f"  Updating eBay listing...")
        if update_listing_images(api, item_id, images):
            print(f"  ✓ Successfully updated!")
            updated += 1
        else:
            print(f"  ✗ Failed to update")
            failed += 1

        time.sleep(1)

    print(f"\n{'='*80}")
    print(f"Results:")
    print(f"  ✓ Updated: {updated}")
    print(f"  ✗ Failed: {failed}")
    print(f"  Total: {len(items)}")
    print(f"{'='*80}\n")

    with open('scrape_results.json', 'w') as f:
        json.dump({
            'updated': updated,
            'failed': failed,
            'total': len(items),
            'cache': model_cache
        }, f, indent=2)


if __name__ == '__main__':
    main()
