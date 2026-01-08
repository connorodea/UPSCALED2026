#!/usr/bin/env python3
"""
Automatically find and upload stock product images to eBay listings
Uses web search and image scraping to find official product photos
"""

import requests
import os
import csv
import time
import json
from dotenv import load_dotenv
from ebay_trading_uploader import EbayTradingAPI
from openai import OpenAI

load_dotenv()


def find_product_images_with_ai(brand: str, model: str, openai_client) -> list:
    """
    Use OpenAI to search the web and find official product images
    """

    # Create a prompt to search for product images
    prompt = f"""Find official stock product images for {brand} {model}.

Search the web and find 2-3 high-quality official product images from:
- Samsung's official website
- Official retailer sites (Best Buy, Amazon, etc.)
- Tech review sites with official product photos

Return ONLY a JSON array of direct image URLs in this exact format:
["https://example.com/image1.jpg", "https://example.com/image2.jpg"]

Requirements:
- URLs must be direct links to JPG/PNG files
- Images should be official product photos (not user photos)
- Prefer high resolution images (1000px+)
- Return 2-3 URLs maximum

Model: {model}
Brand: {brand}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at finding official product images. Return only valid image URLs in JSON array format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        result = response.choices[0].message.content.strip()

        # Try to parse JSON
        # Remove markdown code blocks if present
        if result.startswith('```'):
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
        result = result.strip()

        urls = json.loads(result)

        # Validate URLs
        valid_urls = []
        for url in urls:
            if isinstance(url, str) and url.startswith('http'):
                # Quick validation
                try:
                    resp = requests.head(url, timeout=5, allow_redirects=True)
                    if resp.status_code == 200:
                        valid_urls.append(url)
                except:
                    continue

        return valid_urls[:3]  # Max 3 images

    except Exception as e:
        print(f"  AI search error: {e}")
        return []


def find_images_fallback(brand: str, model: str) -> list:
    """
    Fallback method using direct Samsung image URLs
    """
    model_clean = model.strip().replace(' ', '').replace('-', '').upper()

    # Known Samsung image patterns
    potential_urls = []

    # For watches (SM-R series)
    if model_clean.startswith('SMR'):
        potential_urls.extend([
            f"https://images.samsung.com/is/image/samsung/p6pim/levant/sm-r890nzkamid/gallery/levant-galaxy-watch4-classic-r890-sm-r890nzkamid-thumb-530582474",
            f"https://image-us.samsung.com/SamsungUS/home/mobile/wearables/galaxy-watch4-classic/gallery/Black_Front.jpg",
        ])

    # For tablets (SM-T series)
    elif model_clean.startswith('SMT') or model_clean.startswith('SMP'):
        potential_urls.extend([
            f"https://images.samsung.com/is/image/samsung/{model_clean}",
            f"https://image-us.samsung.com/SamsungUS/home/mobile/tablets/gallery/{model_clean}_Front_Black.jpg",
        ])

    # Test URLs
    valid_urls = []
    for url in potential_urls:
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                valid_urls.append(url)
        except:
            continue

    return valid_urls


def update_listing_images(api: EbayTradingAPI, item_id: str, image_urls: list) -> bool:
    """Update eBay listing with product images"""

    if not image_urls:
        return False

    # Build PictureURL elements
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
                print(f"  Error: {errors[0].get('LongMessage', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False


def main():
    # Load configuration
    dev_id = os.getenv('EBAY_DEV_ID')
    app_id = os.getenv('EBAY_CLIENT_ID')
    cert_id = os.getenv('EBAY_CLIENT_SECRET')
    auth_token = os.getenv('EBAY_AUTH_TOKEN')
    sandbox = os.getenv('EBAY_SANDBOX', 'false').lower() == 'true'
    openai_api_key = os.getenv('OPENAI_API_KEY')

    # Initialize APIs
    api = EbayTradingAPI(dev_id, app_id, cert_id, auth_token, sandbox)
    openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    # Read item mapping
    mapping_file = 'item_mapping.csv'
    if not os.path.exists(mapping_file):
        print(f"Error: {mapping_file} not found")
        return

    print(f"Reading {mapping_file}...")
    with open(mapping_file, 'r') as f:
        reader = csv.DictReader(f)
        items = list(reader)

    print(f"Found {len(items)} items to update")
    print("="*80)

    # Track unique models to avoid redundant searches
    model_image_cache = {}

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

        # Check cache first
        cache_key = f"{brand}_{model}"
        if cache_key in model_image_cache:
            print(f"  Using cached images")
            images = model_image_cache[cache_key]
        else:
            # Search for images
            print(f"  Searching for product images...")

            # Try AI search first if available
            if openai_client:
                images = find_product_images_with_ai(brand, model, openai_client)
                if images:
                    print(f"  ✓ Found {len(images)} images via AI search")
            else:
                images = []

            # Fallback to direct URL patterns
            if not images:
                print(f"  Trying fallback image search...")
                images = find_images_fallback(brand, model)
                if images:
                    print(f"  ✓ Found {len(images)} images via fallback")

            # Cache the results
            model_image_cache[cache_key] = images

        if not images:
            print(f"  ✗ No images found")
            failed += 1
            continue

        # Show found images
        for img_url in images:
            print(f"    - {img_url}")

        # Update listing
        print(f"  Updating listing...")
        if update_listing_images(api, item_id, images):
            print(f"  ✓ Successfully updated")
            updated += 1
        else:
            print(f"  ✗ Failed to update")
            failed += 1

        # Rate limiting
        time.sleep(2)

    print(f"\n{'='*80}")
    print("Summary:")
    print(f"  ✓ Successfully updated: {updated}")
    print(f"  ✗ Failed: {failed}")
    print(f"  Total processed: {len(items)}")
    print(f"{'='*80}\n")

    # Save results
    with open('image_update_results.json', 'w') as f:
        json.dump({
            'updated': updated,
            'failed': failed,
            'total': len(items),
            'model_image_cache': model_image_cache
        }, f, indent=2)

    print("Results saved to image_update_results.json")


if __name__ == '__main__':
    main()
