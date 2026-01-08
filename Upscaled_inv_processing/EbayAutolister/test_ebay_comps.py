#!/usr/bin/env python3
"""
Test eBay Comps Integration - Active Listings with Price Filtering

Demonstrates how the pricing engine uses eBay Browse API to get active listing comps
with intelligent price filtering to exclude accessories.
"""

import sys
sys.path.insert(0, '.')

from ebay_pricing.browse_api import EbayBrowseAPI, analyze_active_competition, _get_minimum_price_filter
from ebay_pricing.pricing_engine import get_pricing_recommendation
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

print("\n" + "="*100)
print(" eBay Active Listing Comps - Integration Test")
print("="*100 + "\n")

# Test products from B2 batch
test_products = [
    {
        "brand": "Nintendo",
        "model": "Switch OLED",
        "condition": "LIKE_NEW",
        "retail_price": 349.99
    },
    {
        "brand": "Apple",
        "model": "MacBook Air M1",
        "condition": "USED_VERY_GOOD",
        "retail_price": 999.00
    },
    {
        "brand": "Microsoft",
        "model": "Surface Pro 7",
        "condition": "USED_GOOD",
        "retail_price": 749.99
    },
    {
        "brand": "Sony",
        "model": "PlayStation 5",
        "condition": "LIKE_NEW",
        "retail_price": 499.99
    }
]

api = EbayBrowseAPI()

for product in test_products:
    brand = product['brand']
    model = product['model']
    condition = product['condition']
    retail_price = product['retail_price']

    print(f"\n{'='*100}")
    print(f"  Product: {brand} {model} ({condition})")
    print(f"  MSRP: ${retail_price:.2f}")
    print(f"{'='*100}\n")

    # Show minimum price filter
    min_price = _get_minimum_price_filter(brand, model)
    print(f"🔍 Search Strategy:")
    print(f"   Query: \"{brand} {model}\"")
    print(f"   Min Price Filter: ${min_price:.2f} (excludes accessories)")
    print(f"   Condition: {condition}")

    # Get active competition stats
    print(f"\n📊 Active eBay Listings:")
    print("-" * 100)

    stats = analyze_active_competition(brand, model, condition)

    if stats['active_listing_count'] > 0:
        print(f"   Found: {stats['active_listing_count']} active listings")
        print(f"   Average Price: ${stats['avg_active_price']:.2f}")
        print(f"   Median Price: ${stats['median_active_price']:.2f}")
        print(f"   Price Range: ${stats['price_range_low']:.2f} - ${stats['price_range_high']:.2f}")
    else:
        print(f"   ⚠️  No active listings found (may be too specific)")

    # Get full pricing recommendation
    print(f"\n💰 Pricing Recommendation:")
    print("-" * 100)

    pricing = get_pricing_recommendation(
        brand=brand,
        model=model,
        condition=condition,
        retail_price=retail_price
    )

    print(f"   Buy-It-Now Price: ${pricing.buy_it_now_price:.2f}")
    if pricing.min_offer_price:
        print(f"   Min Offer: ${pricing.min_offer_price:.2f}")
        print(f"   Auto-Accept: ${pricing.auto_accept_offer:.2f}")
        print(f"   Auto-Decline: ${pricing.auto_decline_offer:.2f}")

    print(f"\n   Confidence: {pricing.confidence:.0%}")
    print(f"   Data Sources: {', '.join(pricing.market_data.sources) if pricing.market_data.sources else 'fallback'}")
    print(f"   Reasoning: {pricing.reasoning}")

    # Show sample listings
    print(f"\n📝 Sample Active Listings:")
    print("-" * 100)

    try:
        results = api.search_active_listings(brand, model, condition, limit=5, min_price=min_price)
        items = results.get('itemSummaries', [])

        if items:
            for i, item in enumerate(items[:5], 1):
                title = item.get('title', 'N/A')
                price_data = item.get('price', {})
                price_value = price_data.get('value', 0)

                try:
                    price = float(price_value) if price_value else 0.0
                except:
                    price = 0.0

                print(f"   {i}. ${price:.2f} - {title[:70]}...")
        else:
            print(f"   No listings found")

    except Exception as e:
        print(f"   Error fetching samples: {e}")

print("\n" + "="*100)
print(" Summary: eBay Browse API Integration")
print("="*100)

print("""
✅ What's Working:
   • OAuth 2.0 authentication with eBay API
   • Active listing searches with price filters
   • Automatic accessory exclusion (min price based on product type)
   • Condition-based filtering
   • Market statistics (avg, median, range)
   • Integration with pricing engine

⚠️  Important Notes:
   • Browse API provides ACTIVE listings only (not sold/completed)
   • Sold comps come from Tavily web search + OpenAI extraction
   • Price filters help exclude accessories, cases, parts
   • Pricing formula:
     - With sold comps: (avg_sold * 0.92) * (1 - condition_penalty)
     - With active only: (avg_active * 0.95) * (1 - condition_penalty)
     - Fallback: (retail * 0.50) * (1 - condition_penalty)

📈 Data Flow:
   1. Check cache (24hr TTL)
   2. Fetch sold comps via Tavily (if cache miss)
   3. Fetch active listings via eBay Browse API
   4. Calculate pricing with confidence score
   5. Cache results for 24 hours
""")

print("="*100 + "\n")
