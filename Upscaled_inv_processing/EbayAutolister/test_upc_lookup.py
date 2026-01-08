#!/usr/bin/env python3
"""
Test UPC lookup with real B2 batch UPC codes
"""

import sys
sys.path.insert(0, '.')

from ebay_pricing.upc_lookup import lookup_product
from ebay_pricing.pricing_engine import get_pricing_recommendation
from config import CONDITION_MAPPINGS

def normalize_condition(grade):
    grade_map = {
        'LN': 'LIKE_NEW',
        'VG': 'USED_VERY_GOOD',
        'G': 'USED_GOOD',
        'AC': 'USED_ACCEPTABLE',
        'SA': 'FOR_PARTS_OR_NOT_WORKING'
    }
    return grade_map.get(grade.upper(), 'USED_GOOD')

# B2 items WITH UPC codes
test_items = [
    {'sku': 'LN-DEN001-B2UID003', 'brand': 'Nintendo', 'model': '', 'upc': '0045496882648', 'grade': 'LN'},
    # Add more items with UPCs from your B2 batch if available
]

print("\n" + "="*100)
print(" UPC LOOKUP TEST - Enhanced Product Identification")
print("="*100 + "\n")

for item in test_items:
    sku = item['sku']
    brand = item['brand']
    model = item['model']
    upc = item['upc']
    grade = item['grade']
    condition = normalize_condition(grade)

    print(f"\n{'='*100}")
    print(f"  SKU: {sku}")
    print(f"  Input: {brand} {model}")
    print(f"  UPC: {upc}")
    print(f"  Grade: {grade}")
    print("-"*100)

    # Test UPC lookup
    print("\n  🔍 UPC LOOKUP:")
    upc_data = lookup_product(upc)

    if upc_data:
        print(f"     ✅ Found: {upc_data['title']}")
        print(f"     Brand: {upc_data['brand']}")
        print(f"     Model: {upc_data['model']}")
        print(f"     Category: {upc_data['category']}")
        if upc_data.get('msrp'):
            print(f"     MSRP: ${upc_data['msrp']:.2f}")
        print(f"     Source: {upc_data['source']}")
    else:
        print(f"     ❌ Not found in UPC databases")
        print(f"     (Falling back to model number search)")

    # Test pricing with UPC
    print("\n  💰 PRICING WITH UPC:")
    pricing = get_pricing_recommendation(
        brand=brand,
        model=model if model else brand,
        condition=condition,
        retail_price=None,
        upc=upc
    )

    print(f"     Buy-It-Now: ${pricing.buy_it_now_price:.2f}")
    if pricing.min_offer_price:
        print(f"     Min Offer: ${pricing.min_offer_price:.2f}")

    if pricing.market_data:
        print(f"\n  📊 MARKET DATA:")
        print(f"     Sold Comps: {pricing.market_data.sold_count}")
        if pricing.market_data.sold_count > 0:
            print(f"     Avg Sold: ${pricing.market_data.avg_sold_price:.2f}")

    print(f"\n  📈 CONFIDENCE: {pricing.confidence:.0%}")
    print(f"     {pricing.reasoning}")

print("\n" + "="*100)
print("\n✅ UPC lookup integration test complete!\n")

print("="*100)
print(" SETUP INSTRUCTIONS")
print("="*100)
print("""
To enable UPC lookups:

1. Sign up for FREE API key at: https://www.upcitemdb.com/
   - Free tier: 100 lookups/day
   - No credit card required

2. Add to your .env file:
   UPCITEMDB_API_KEY=your_key_here

3. Run pricing with UPC codes from your CSV!

Alternative free options:
- OpenFoodFacts (food/consumer goods only)
- Build your own UPC database over time
""")
print("="*100 + "\n")
