#!/usr/bin/env python3
"""Debug price filter"""

import sys
sys.path.insert(0, '.')

from ebay_pricing.browse_api import EbayBrowseAPI
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

api = EbayBrowseAPI()
api.authenticate()

print("\n" + "="*100)
print("Testing Price Filter: Nintendo Switch OLED")
print("="*100 + "\n")

# Test with min_price=100
results = api.search_active_listings(
    brand="Nintendo",
    model="Switch OLED",
    condition="LIKE_NEW",
    limit=10,
    min_price=100.0
)

items = results.get('itemSummaries', [])
total = results.get('total', 0)

print(f"\nTotal matches: {total}")
print(f"Items returned: {len(items)}\n")

if items:
    print("First 10 listings:")
    for i, item in enumerate(items, 1):
        title = item.get('title', 'N/A')
        price_data = item.get('price', {})
        price = float(price_data.get('value', 0))

        print(f"{i:2d}. ${price:7.2f} - {title[:70]}")
else:
    print("No listings found!")

print("\n" + "="*100 + "\n")
