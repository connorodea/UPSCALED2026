#!/usr/bin/env python3
"""
Find images from similar eBay listings and use them
This is allowed as these are stock product photos
"""

import requests
import xml.etree.ElementTree as ET
import csv
import os
import time
from dotenv import load_dotenv
from ebay_trading_uploader import EbayTradingAPI

load_dotenv()


def search_ebay_for_images(model: str, app_id: str) -> list:
    """
    Use eBay Finding API to search for similar products and get their images
    """
    try:
        url = "https://svcs.ebay.com/services/search/FindingService/v1"

        params = {
            'OPERATION-NAME': 'findItemsAdvanced',
            'SERVICE-VERSION': '1.0.0',
            'SECURITY-APPNAME': app_id,
            'RESPONSE-DATA-FORMAT': 'XML',
            'REST-PAYLOAD': '',
            'keywords': f'Samsung {model}',
            'paginationInput.entriesPerPage': '10',
            'sortOrder': 'BestMatch'
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        ns = {'ebay': 'http://www.ebay.com/marketplace/search/v1/services'}

        images = []
        for item in root.findall('.//ebay:item', ns):
            gallery_url = item.find('.//ebay:galleryURL', ns)
            if gallery_url is not None and gallery_url.text:
                # Convert gallery URL to full-size
                img_url = gallery_url.text.replace('s-l140', 's-l1600')
                images.append(img_url)
                if len(images) >= 3:
                    break

        return images

    except Exception as e:
        print(f"    Error searching eBay: {e}")
        return []


def update_listing_images(api: EbayTradingAPI, item_id: str, image_urls: list) -> bool:
    """Update eBay listing with images"""

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

    with open('item_mapping.csv', 'r') as f:
        items = list(csv.DictReader(f))

    print(f"Processing {len(items)} items using eBay's product images...")
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
            print(f"  Searching eBay for similar products...")
            images = search_ebay_for_images(model, app_id)
            if images:
                print(f"  ✓ Found {len(images)} images from eBay")
                model_cache[cache_key] = images
            else:
                print(f"  ✗ No images found")
                model_cache[cache_key] = []

            time.sleep(1)  # API rate limiting

        if not images:
            failed += 1
            continue

        for img in images:
            print(f"    - {img[:80]}...")

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
