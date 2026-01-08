#!/usr/bin/env python3
"""
Test eBay Browse API Integration

Tests OAuth authentication and active listing searches to verify the Browse API works.
"""

import sys
sys.path.insert(0, '.')

from ebay_pricing.browse_api import EbayBrowseAPI, analyze_active_competition
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "="*100)
print(" eBay Browse API - Authentication & Search Test")
print("="*100 + "\n")

# Test 1: OAuth Authentication
print("TEST 1: OAuth Authentication")
print("-" * 100)

api = EbayBrowseAPI()

print(f"Client ID: {api.client_id[:20]}...")
print(f"Sandbox Mode: {api.sandbox}")
print(f"OAuth URL: {api.oauth_url}")
print(f"Base URL: {api.base_url}")

print("\nAttempting OAuth authentication...")

if api.authenticate():
    print("✅ Authentication SUCCESSFUL!")
    print(f"   Access Token: {api.access_token[:50]}...")
    print(f"   Token Expires: {api.token_expires_at}")
else:
    print("❌ Authentication FAILED!")
    print("   Check your EBAY_CLIENT_ID and EBAY_CLIENT_SECRET in .env")
    sys.exit(1)

# Test 2: Search Active Listings
print("\n" + "="*100)
print("TEST 2: Search Active Listings")
print("="*100 + "\n")

test_searches = [
    {"brand": "Apple", "model": "MacBook Air M1", "condition": "USED_VERY_GOOD"},
    {"brand": "Nintendo", "model": "Switch OLED", "condition": "LIKE_NEW"},
    {"brand": "Microsoft", "model": "Surface Pro 7", "condition": "USED_GOOD"},
]

for search in test_searches:
    print(f"\nSearching: {search['brand']} {search['model']} ({search['condition']})")
    print("-" * 100)

    try:
        results = api.search_active_listings(
            brand=search['brand'],
            model=search['model'],
            condition=search['condition'],
            limit=20
        )

        total = results.get('total', 0)
        items = results.get('itemSummaries', [])

        print(f"Total matches: {total}")
        print(f"Items returned: {len(items)}")

        if items:
            print(f"\nFirst 5 listings:")
            for i, item in enumerate(items[:5], 1):
                title = item.get('title', 'N/A')
                price_data = item.get('price', {})
                price_value = price_data.get('value', 0)

                # Convert price to float if it's a string
                try:
                    price = float(price_value) if price_value else 0.0
                except (ValueError, TypeError):
                    price = 0.0

                currency = price_data.get('currency', 'USD')
                condition = item.get('condition', 'N/A')

                print(f"  {i}. ${price:.2f} {currency} - {title[:60]}...")
                print(f"     Condition: {condition}")
        else:
            print("No listings found")

    except Exception as e:
        print(f"❌ Search failed: {e}")

# Test 3: Analyze Active Competition (Full Stats)
print("\n" + "="*100)
print("TEST 3: Active Competition Analysis")
print("="*100 + "\n")

print("Analyzing: Nintendo Switch OLED (LIKE_NEW)")
print("-" * 100)

stats = analyze_active_competition("Nintendo", "Switch OLED", "LIKE_NEW")

print(f"\n📊 Competition Statistics:")
print(f"   Active Listings: {stats['active_listing_count']}")
print(f"   Average Price: ${stats['avg_active_price']:.2f}")
print(f"   Median Price: ${stats['median_active_price']:.2f}")
print(f"   Price Range: ${stats['price_range_low']:.2f} - ${stats['price_range_high']:.2f}")

if stats['active_listing_count'] > 0:
    print(f"\n✅ Browse API Integration Working!")
    print(f"   Competitive pricing data available for automated pricing engine")
else:
    print(f"\n⚠️  No active listings found")
    print(f"   This is normal for very specific queries")

# Test 4: Integration with Pricing Engine
print("\n" + "="*100)
print("TEST 4: Integration with Pricing Engine")
print("="*100 + "\n")

from ebay_pricing.pricing_engine import get_pricing_recommendation

print("Testing: Apple MacBook Air M1 (LIKE_NEW)")
print("-" * 100)

pricing = get_pricing_recommendation(
    brand="Apple",
    model="MacBook Air M1",
    condition="LIKE_NEW",
    retail_price=999.00  # Known MSRP
)

print(f"\n💰 Pricing Recommendation:")
print(f"   Buy-It-Now: ${pricing.buy_it_now_price:.2f}")
print(f"   Min Offer: ${pricing.min_offer_price:.2f}" if pricing.min_offer_price else "   Min Offer: N/A")
print(f"   Confidence: {pricing.confidence:.0%}")
print(f"   Reasoning: {pricing.reasoning}")

if pricing.market_data:
    print(f"\n📊 Market Data:")
    print(f"   Sold Comps: {pricing.market_data.sold_count}")
    print(f"   Active Listings: {pricing.market_data.active_listing_count}")
    print(f"   Data Sources: {', '.join(pricing.market_data.sources)}")

print("\n" + "="*100)
print("✅ eBay Browse API Integration Complete!")
print("="*100)

print("\n📝 IMPORTANT NOTES:")
print("   • Browse API provides ACTIVE listing data only")
print("   • Sold/completed listings NOT available via eBay API (deprecated Oct 2020)")
print("   • For sold comps, we use Tavily web search + OpenAI extraction")
print("   • Active listing data is used when sold comps unavailable")
print("   • Pricing formula: price = (sold_avg * 0.92) or (active_avg * 0.95)")
print("\n")
