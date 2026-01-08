#!/usr/bin/env python3
"""
Find stock images and update eBay listings
Uses web search to find official product images
"""

import requests
import os
import csv
import json
import time
from dotenv import load_dotenv
from ebay_trading_uploader import EbayTradingAPI

load_dotenv()


def search_google_images(query: str, api_key: str = None, cx: str = None) -> list:
    """
    Search Google Images for product photos
    Requires Google Custom Search API key and CX
    Free tier: 100 queries/day
    """
    if not api_key or not cx:
        return []

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cx,
        'q': query,
        'searchType': 'image',
        'num': 3,  # Get top 3 images
        'imgSize': 'large',
        'safe': 'active'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if 'items' in data:
            return [item['link'] for item in data['items'][:3]]
    except Exception as e:
        print(f"  Error searching images: {e}")

    return []


def find_samsung_product_images(model: str) -> list:
    """
    Try to find Samsung product images from various sources
    """
    model_clean = model.strip().replace(' ', '').upper()

    # Common Samsung image CDN patterns
    images = []

    # Pattern 1: Samsung US image server
    base_urls = [
        f"https://image-us.samsung.com/SamsungUS/home/mobile/galaxy-watches/gallery/{model_clean}_Black_Front.jpg",
        f"https://images.samsung.com/is/image/samsung/{model_clean}",
        f"https://image-us.samsung.com/SamsungUS/home/mobile/tablets/pdp/{model_clean}-Front-Black.jpg"
    ]

    # Test which URLs are valid
    for url in base_urls:
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                images.append(url)
                if len(images) >= 3:
                    break
        except:
            continue

    return images


def update_listing_with_images(api: EbayTradingAPI, item_id: str, image_urls: list) -> bool:
    """Update eBay listing with product images"""

    if not image_urls:
        return False

    # Build PictureURL elements
    picture_urls = '\n'.join([f'            <PictureURL>{url}</PictureURL>' for url in image_urls[:12]])  # eBay max 12 images

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
            print(f"  Response: {response.get('Errors', [{}])[0].get('LongMessage', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    # Load configuration
    dev_id = os.getenv('EBAY_DEV_ID')
    app_id = os.getenv('EBAY_CLIENT_ID')
    cert_id = os.getenv('EBAY_CLIENT_SECRET')
    auth_token = os.getenv('EBAY_AUTH_TOKEN')
    sandbox = os.getenv('EBAY_SANDBOX', 'false').lower() == 'true'

    # Optional: Google Custom Search API (for better image finding)
    google_api_key = os.getenv('GOOGLE_API_KEY', '')
    google_cx = os.getenv('GOOGLE_CX', '')

    api = EbayTradingAPI(dev_id, app_id, cert_id, auth_token, sandbox)

    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        mapping_file = sys.argv[1]
    else:
        mapping_file = 'item_mapping.csv'

    if not os.path.exists(mapping_file):
        print(f"Error: {mapping_file} not found")
        print("\nPlease provide a CSV file with columns: sku,item_id,brand,model")
        print("Example:")
        print("  LN-DEN001-B1UID001-BIN001,306631123381,Samsung,SM-R890")
        return

    # Process the mapping file
    print(f"\nReading {mapping_file}...")
    updated = 0
    failed = 0
    skipped = 0

    with open(mapping_file, 'r') as f:
        reader = csv.DictReader(f)
        items = list(reader)

    print(f"Found {len(items)} items to process")
    print("="*80)

    for idx, item in enumerate(items, 1):
        sku = item['sku']
        item_id = item['item_id']
        brand = item['brand']
        model = item['model']

        if item_id == 'ITEM_ID_HERE' or not item_id:
            skipped += 1
            continue

        print(f"\n[{idx}/{len(items)}] {brand} {model}")
        print(f"  Item ID: {item_id}")

        # Try to find images
        print(f"  Searching for product images...")
        images = find_samsung_product_images(model)

        if not images and google_api_key and google_cx:
            print(f"  Trying Google Image Search...")
            images = search_google_images(f"{brand} {model} official product", google_api_key, google_cx)

        if not images:
            print(f"  ⚠ No images found")
            failed += 1
            continue

        print(f"  Found {len(images)} image(s)")
        for img_url in images:
            print(f"    - {img_url}")

        # Update listing
        print(f"  Updating listing...")
        if update_listing_with_images(api, item_id, images):
            print(f"  ✓ Successfully updated")
            updated += 1
        else:
            print(f"  ✗ Failed to update")
            failed += 1

        time.sleep(1)  # Rate limiting

    print(f"\n{'='*80}")
    print("Summary:")
    print(f"  ✓ Updated: {updated}")
    print(f"  ✗ Failed: {failed}")
    print(f"  ⊝ Skipped: {skipped}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
