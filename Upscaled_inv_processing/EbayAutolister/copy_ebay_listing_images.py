#!/usr/bin/env python3
"""
Find active eBay listings for the same Samsung models
and copy their product images to our listings
"""

import requests
import xml.etree.ElementTree as ET
import os
import csv
import time
from dotenv import load_dotenv
from ebay_trading_uploader import EbayTradingAPI

load_dotenv()


def find_similar_listing_images(model: str, api: EbayTradingAPI) -> list:
    """
    Use eBay Shopping API to find similar active listings
    and extract their image URLs
    """
    try:
        url = "https://open.api.ebay.com/shopping"

        params = {
            'callname': 'FindProducts',
            'responseencoding': 'XML',
            'appid': api.app_id,
            'siteid': '0',
            'version': '1189',
            'QueryKeywords': f'Samsung {model}',
            'MaxEntries': '5',
            'AvailableItemsOnly': 'true',
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        ns = {'ebay': 'urn:ebay:apis:eBLBaseComponents'}

        images = []
        for product in root.findall('.//ebay:Product', ns):
            stock_photo_url = product.find('.//ebay:StockPhotoURL', ns)
            if stock_photo_url is not None and stock_photo_url.text:
                img_url = stock_photo_url.text
                # Try to get larger version
                img_url = img_url.replace('s-l140', 's-l1600').replace('s-l225', 's-l1600')
                images.append(img_url)
                if len(images) >= 3:
                    break

        return images

    except Exception as e:
        print(f"    Search error: {e}")
        return []


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
                error_msg = errors[0].get('LongMessage', 'Unknown')
                print(f"    Error: {error_msg}")
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

    with open('item_mapping.csv', 'r') as f:
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

        # Check cache
        cache_key = model.upper()
        if cache_key in model_cache:
            print(f"  Using cached images")
            images = model_cache[cache_key]
        else:
            print(f"  Searching for similar eBay listings...")
            images = find_similar_listing_images(model, api)
            model_cache[cache_key] = images

            if images:
                print(f"  ✓ Found {len(images)} images")
                for img in images:
                    print(f"    - {img[:80]}...")
            else:
                print(f"  ✗ No images found")

            time.sleep(1)  # Rate limiting

        if not images:
            failed += 1
            continue

        print(f"  Updating listing...")
        if update_listing_images(api, item_id, images):
            print(f"  ✓ Successfully updated!")
            updated += 1
        else:
            print(f"  ✗ Failed to update")
            failed += 1

        time.sleep(1)

    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  ✓ Updated: {updated}")
    print(f"  ✗ Failed: {failed}")
    print(f"  Total: {len(items)}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
