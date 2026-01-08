#!/usr/bin/env python3
"""
Test eBay Comps Integration with Real B2 Batch Inventory

Uses the first 5 items from your B2 batch to demonstrate real-world pricing
with eBay Browse API active listing comps.
"""

import sys
sys.path.insert(0, '.')

from ebay_pricing.pricing_engine import get_pricing_recommendation
from ebay_pricing.browse_api import _get_minimum_price_filter
import logging

# Minimal logging
logging.basicConfig(level=logging.WARNING)

# First 5 items from B2 batch
b2_items = [
    {
        "sku": "LN-DEN001-B2UID001",
        "brand": "Nintendo",
        "model": "Switch OLED",
        "upc": "0045496882648",
        "grade": "LN",
        "retail_price": 349.99
    },
    {
        "sku": "LN-DEN001-B2UID002",
        "brand": "Apple",
        "model": "MacBook Air",
        "upc": "",
        "grade": "LN",
        "retail_price": 999.00
    },
    {
        "sku": "VG-DEN001-B2UID003",
        "brand": "Microsoft",
        "model": "Surface Pro 7",
        "upc": "",
        "grade": "VG",
        "retail_price": 749.99
    },
    {
        "sku": "LN-DEN001-B2UID004",
        "brand": "Sony",
        "model": "PlayStation 5",
        "upc": "",
        "grade": "LN",
        "retail_price": 499.99
    },
    {
        "sku": "VG-DEN001-B2UID005",
        "brand": "Apple",
        "model": "iPad Pro 11",
        "upc": "",
        "grade": "VG",
        "retail_price": 799.00
    }
]

# Condition mapping
condition_map = {
    'LN': 'LIKE_NEW',
    'VG': 'USED_VERY_GOOD',
    'G': 'USED_GOOD',
    'AC': 'USED_ACCEPTABLE',
    'SA': 'FOR_PARTS_OR_NOT_WORKING'
}

print("\n" + "="*100)
print(" B2 Batch Pricing - With eBay Active Listing Comps")
print("="*100 + "\n")

results = []

for item in b2_items:
    sku = item['sku']
    brand = item['brand']
    model = item['model']
    upc = item['upc']
    grade = item['grade']
    retail_price = item['retail_price']
    condition = condition_map[grade]

    print(f"\n{'─'*100}")
    print(f"SKU: {sku}")
    print(f"Product: {brand} {model} ({condition})")
    print(f"MSRP: ${retail_price:.2f}")

    min_price = _get_minimum_price_filter(brand, model)
    print(f"Price Filter: ≥${min_price:.0f} (excludes accessories)")
    print(f"{'─'*100}")

    # Get pricing recommendation
    pricing = get_pricing_recommendation(
        brand=brand,
        model=model,
        condition=condition,
        retail_price=retail_price,
        upc=upc if upc else None
    )

    # Store results
    results.append({
        'sku': sku,
        'product': f"{brand} {model}",
        'bin': pricing.buy_it_now_price,
        'confidence': pricing.confidence,
        'sources': ', '.join(pricing.market_data.sources) if pricing.market_data.sources else 'fallback',
        'sold_comps': pricing.market_data.sold_count if pricing.market_data else 0,
        'active_listings': pricing.market_data.active_listing_count if pricing.market_data else 0
    })

    # Display pricing
    print(f"\n💰 PRICING:")
    print(f"   Buy-It-Now:  ${pricing.buy_it_now_price:.2f}")
    if pricing.min_offer_price:
        print(f"   Min Offer:   ${pricing.min_offer_price:.2f}")
        print(f"   Auto-Accept: ${pricing.auto_accept_offer:.2f}")
        print(f"   Auto-Decline: ${pricing.auto_decline_offer:.2f}")

    print(f"\n📊 MARKET DATA:")
    if pricing.market_data:
        print(f"   Sold Comps (30d): {pricing.market_data.sold_count}")
        if pricing.market_data.sold_count > 0:
            print(f"   Avg Sold: ${pricing.market_data.avg_sold_price:.2f}")
        print(f"   Active Listings: {pricing.market_data.active_listing_count}")
        if pricing.market_data.active_listing_count > 0:
            print(f"   Avg Active: ${pricing.market_data.avg_active_price:.2f}")
        print(f"   Data Sources: {', '.join(pricing.market_data.sources)}")
    else:
        print(f"   No market data available")

    print(f"\n📈 CONFIDENCE: {pricing.confidence:.0%}")
    print(f"   {pricing.reasoning}")

print("\n" + "="*100)
print(" Summary")
print("="*100 + "\n")

# Summary table
print(f"{'SKU':<25} {'Product':<30} {'BIN Price':<12} {'Conf':<6} {'Data Sources':<20}")
print("─" * 100)

for r in results:
    print(f"{r['sku']:<25} {r['product']:<30} ${r['bin']:<11.2f} {r['confidence']:<5.0%} {r['sources']:<20}")

print("─" * 100)

# Statistics
total_bin = sum(r['bin'] for r in results)
avg_bin = total_bin / len(results)
avg_confidence = sum(r['confidence'] for r in results) / len(results)
items_with_comps = sum(1 for r in results if r['sold_comps'] > 0 or r['active_listings'] > 0)

print(f"\nTotal Items: {len(results)}")
print(f"Avg BIN Price: ${avg_bin:.2f}")
print(f"Avg Confidence: {avg_confidence:.0%}")
print(f"Items with Market Data: {items_with_comps}/{len(results)} ({items_with_comps/len(results):.0%})")

print("\n" + "="*100)
print("\n✅ eBay Browse API Integration Complete!")
print("   • Active listing comps integrated")
print("   • Smart price filtering excludes accessories")
print("   • Automatic fallback chain ensures all items priced")
print("   • 24-hour caching minimizes API costs")
print("\n")
