#!/usr/bin/env python3
"""
Use Samsung's official product images directly
Constructs URLs based on Samsung's image CDN patterns
"""

import requests
import os
import csv
import time
from dotenv import load_dotenv
from ebay_trading_uploader import EbayTradingAPI

load_dotenv()


# Samsung official image mappings
SAMSUNG_PRODUCT_IMAGES = {
    # Galaxy Watch 4 Classic 46mm
    'SM-R890': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-r890nzkamid/gallery/levant-galaxy-watch4-classic-r890-sm-r890nzkamid-530582467',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-r890nzkamid/gallery/levant-galaxy-watch4-classic-r890-sm-r890nzkamid-530582468',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-r890nzkamid/gallery/levant-galaxy-watch4-classic-r890-sm-r890nzkamid-530582469',
    ],

    # Galaxy Watch 4 40mm
    'SM-R865U': [
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-r865uzkaxac/gallery/ca-galaxy-watch4-r865-sm-r865uzkaxac-530635684',
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-r865uzkaxac/gallery/ca-galaxy-watch4-r865-sm-r865uzkaxac-530635685',
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-r865uzkaxac/gallery/ca-galaxy-watch4-r865-sm-r865uzkaxac-530635686',
    ],

    # Gear Sport
    'SM-R820': [
        'https://images.samsung.com/is/image/samsung/p5/ae_en/wearables/galaxy-watch/buy/GearSport_Blue.png',
        'https://images.samsung.com/is/image/samsung/p5/levant_en/wearables/sm-r600nzkamid/gallery/levant_en-gear-sport-sm-r820-sm-r820nzkamid-135893896',
    ],

    # Galaxy Watch 4 44mm
    'SM-R870': [
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-r870nzkaxac/gallery/ca-galaxy-watch4-r870-sm-r870nzkaxac-530581836',
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-r870nzkaxac/gallery/ca-galaxy-watch4-r870-sm-r870nzkaxac-530581837',
    ],

    # Gear S3 Classic
    'SM-R830': [
        'https://images.samsung.com/is/image/samsung/p5/global/wearables/sm-r770nzsabtu/gallery/global-gear-s3-classic-r770-sm-r770nzsabtu-69250959',
        'https://images.samsung.com/is/image/samsung/p5/levant_en/wearables/sm-r770nzsabtu/gallery/levant_en-gear-s3-classic-r770-sm-r770nzsabtu-69250957',
    ],

    # Gear S3 Frontier
    'SM-R760': [
        'https://images.samsung.com/is/image/samsung/p5/global/wearables/sm-r760ndaabtu/gallery/global-gear-s3-frontier-r760-sm-r760ndaabtu-69250929',
        'https://images.samsung.com/is/image/samsung/p5/levant_en/wearables/sm-r760ndaabtu/gallery/levant_en-gear-s3-frontier-r760-sm-r760ndaabtu-69250927',
    ],

    # Galaxy Watch 4 42mm
    'SM-R860': [
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-r860nzkaxac/gallery/ca-galaxy-watch4-classic-r860-sm-r860nzkaxac-530582455',
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-r860nzkaxac/gallery/ca-galaxy-watch4-classic-r860-sm-r860nzkaxac-530582456',
    ],

    # Galaxy Watch
    'SM-R810': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-r810nzdamid/gallery/levant-galaxy-watch-r810-sm-r810nzdamid-frontsilverblack-135893794',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-r810nzdamid/gallery/levant-galaxy-watch-r810-sm-r810nzdamid-frontsilverblack-135893795',
    ],

    # Galaxy Tab A 10.1"
    'SM-T510': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t510nzkdmid/gallery/levant-galaxy-tab-a-10-1-2019-sm-t510-sm-t510nzkdmid-frontblack-156533775',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t510nzkdmid/gallery/levant-galaxy-tab-a-10-1-2019-sm-t510-sm-t510nzkdmid-frontblack-156533776',
    ],

    # Galaxy Tab A 8.0"
    'SM-T290': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t290nzkamid/gallery/levant-galaxy-tab-a-8-0-2019-sm-t290-sm-t290nzkamid-frontblack-156533796',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t290nzkamid/gallery/levant-galaxy-tab-a-8-0-2019-sm-t290-sm-t290nzkamid-frontblack-156533797',
    ],

    # Galaxy Tab S6 Lite
    'SM-P610': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-p610nzaamid/gallery/levant-galaxy-tab-s6-lite-wifi-p610-sm-p610nzaamid-frontgraywithpen-239841316',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-p610nzaamid/gallery/levant-galaxy-tab-s6-lite-wifi-p610-sm-p610nzaamid-frontgraywithpen-239841317',
    ],
    'SM-P610NZAAXAR': [
        'https://images.samsung.com/is/image/samsung/p6pim/us/sm-p610nzaaxar/gallery/us-galaxy-tab-s6-lite-wifi-p610-sm-p610nzaaxar-frontgraywithpen-231482814',
        'https://images.samsung.com/is/image/samsung/p6pim/us/sm-p610nzaaxar/gallery/us-galaxy-tab-s6-lite-wifi-p610-sm-p610nzaaxar-frontgraywithpen-231482815',
    ],

    # Galaxy Tab A7
    'SM-T500': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t500nzaamid/gallery/levant-galaxy-tab-a7-wi-fi-t500-sm-t500nzaamid-frontgray-279885055',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t500nzaamid/gallery/levant-galaxy-tab-a7-wi-fi-t500-sm-t500nzaamid-frontgray-279885056',
    ],
    'SM-T500NZAAXAR': [
        'https://images.samsung.com/is/image/samsung/p6pim/us/sm-t500nzaaxar/gallery/us-galaxy-tab-a7-wi-fi-t500-sm-t500nzaaxar-frontgray-279884815',
        'https://images.samsung.com/is/image/samsung/p6pim/us/sm-t500nzaaxar/gallery/us-galaxy-tab-a7-wi-fi-t500-sm-t500nzaaxar-frontgray-279884816',
    ],

    # Galaxy Tab A 8.0" (2017)
    'SM-T380': [
        'https://images.samsung.com/is/image/samsung/p5/levant_en/tablets/sm-t385nzkamid/gallery/levant_en-galaxy-tab-a-2017-with-s-pen-t385-sm-t385nzkamid-frontblack-119922689',
        'https://images.samsung.com/is/image/samsung/p5/levant_en/tablets/sm-t385nzkamid/gallery/levant_en-galaxy-tab-a-2017-with-s-pen-t385-sm-t385nzkamid-frontblack-119922690',
    ],

    # Galaxy Tab S5e
    'SM-T720': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t720nzsemid/gallery/levant-galaxy-tab-s5e-t720-sm-t720nzsemid-frontsilver-156533698',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t720nzsemid/gallery/levant-galaxy-tab-s5e-t720-sm-t720nzsemid-frontsilver-156533699',
    ],

    # Galaxy Tab S7
    'SM-T870': [
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-t870nzkaxac/gallery/ca-galaxy-tab-s7-t870-sm-t870nzkaxac-frontblack-231482671',
        'https://images.samsung.com/is/image/samsung/p6pim/ca/sm-t870nzkaxac/gallery/ca-galaxy-tab-s7-t870-sm-t870nzkaxac-frontblack-231482672',
    ],
    'SM-T870NZKAXAR': [
        'https://images.samsung.com/is/image/samsung/p6pim/us/sm-t870nzkaxar/gallery/us-galaxy-tab-s7-t870-sm-t870nzkaxar-frontblack-231482556',
        'https://images.samsung.com/is/image/samsung/p6pim/us/sm-t870nzkaxar/gallery/us-galaxy-tab-s7-t870-sm-t870nzkaxar-frontblack-231482557',
    ],

    # Galaxy Tab S6
    'SM-T860': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t860nzaamid/gallery/levant-galaxy-tab-s6-t860-sm-t860nzaamid-frontgraywithpen-156533761',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t860nzaamid/gallery/levant-galaxy-tab-s6-t860-sm-t860nzaamid-frontgraywithpen-156533762',
    ],

    # Galaxy Tab 4 7.0"
    'SM-T220': [
        'https://images.samsung.com/is/image/samsung/p5/ae_en/tablets/sm-t230nzwaxsg/gallery/ae_en-galaxy-tab-4-7-0-t230-sm-t230nzwaxsg-63104761',
    ],
    'SM-T220NZAAXAR': [
        'https://images.samsung.com/is/image/samsung/p5/ae_en/tablets/sm-t230nzwaxsg/gallery/ae_en-galaxy-tab-4-7-0-t230-sm-t230nzwaxsg-63104761',
    ],

    'SM-T290NZKAXAR': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t290nzkamid/gallery/levant-galaxy-tab-a-8-0-2019-sm-t290-sm-t290nzkamid-frontblack-156533796',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t290nzkamid/gallery/levant-galaxy-tab-a-8-0-2019-sm-t290-sm-t290nzkamid-frontblack-156533797',
    ],
    'SM-T290NZSKXAR': [
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t290nzkamid/gallery/levant-galaxy-tab-a-8-0-2019-sm-t290-sm-t290nzkamid-frontblack-156533796',
        'https://images.samsung.com/is/image/samsung/p6pim/levant/sm-t290nzkamid/gallery/levant-galaxy-tab-a-8-0-2019-sm-t290-sm-t290nzkamid-frontblack-156533797',
    ],
}


def get_model_base(model: str) -> str:
    """Extract base model from variants like SM-T500NZAAXAR -> SM-T500"""
    clean = model.strip().upper().replace('-', '')
    if clean.startswith('SM'):
        # Extract base model number (e.g., SMT500 from SMT500NZAAXAR)
        if len(clean) >= 7:
            base = clean[:7]  # SM + letter + 4 digits
            # Try exact match first
            if model in SAMSUNG_PRODUCT_IMAGES:
                return model
            # Try base
            base_with_dash = base[:3] + '-' + base[3:]
            if base_with_dash in SAMSUNG_PRODUCT_IMAGES:
                return base_with_dash
    return model


def validate_image_url(url: str) -> bool:
    """Quick check if image URL is accessible"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return False


def get_images_for_model(model: str) -> list:
    """Get Samsung official images for a model"""
    # Try exact match
    if model in SAMSUNG_PRODUCT_IMAGES:
        images = SAMSUNG_PRODUCT_IMAGES[model]
    else:
        # Try base model
        base = get_model_base(model)
        images = SAMSUNG_PRODUCT_IMAGES.get(base, [])

    # Validate URLs
    valid_images = []
    for url in images[:3]:  # Max 3 images
        if validate_image_url(url):
            valid_images.append(url)
            print(f"    ✓ Valid: {url[:80]}...")
        else:
            print(f"    ✗ Invalid: {url[:80]}...")

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

    with open('item_mapping.csv', 'r') as f:
        items = list(csv.DictReader(f))

    print(f"Processing {len(items)} items with Samsung official images...")
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
            print(f"  Looking up Samsung official images...")
            images = get_images_for_model(model)
            model_cache[cache_key] = images

            if images:
                print(f"  ✓ Found {len(images)} valid Samsung official images")
            else:
                print(f"  ✗ No images found for this model")

        if not images:
            failed += 1
            continue

        print(f"  Updating eBay listing...")
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
