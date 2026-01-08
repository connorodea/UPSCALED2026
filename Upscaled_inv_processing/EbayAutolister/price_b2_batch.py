#!/usr/bin/env python3
"""
Price B2 batch inventory using Tavily web search for market data
"""

import sys
import os
import pandas as pd
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ebay_pricing.pricing_engine import get_pricing_recommendation
from config import CONDITION_MAPPINGS

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def normalize_condition(grade):
    """Convert grade codes to eBay conditions"""
    grade_map = {
        'LN': 'LIKE_NEW',
        'VG': 'USED_VERY_GOOD',
        'G': 'USED_GOOD',
        'AC': 'USED_ACCEPTABLE',
        'SA': 'FOR_PARTS_OR_NOT_WORKING'
    }
    return grade_map.get(grade.upper(), 'USED_GOOD')

# B2 Batch Data
b2_items = [
    {'sku': 'LN-DEN001-B2UID001', 'brand': 'Apple', 'model': 'A2449', 'grade': 'LN', 'notes': 'like new'},
    {'sku': 'VG-DEN001-B2UID002', 'brand': 'Apple', 'model': 'A1347', 'grade': 'VG', 'notes': 'very good'},
    {'sku': 'LN-DEN001-B2UID005', 'brand': 'Microsoft', 'model': 'Surface 1866', 'grade': 'LN', 'notes': 'pristine'},
    {'sku': 'VG-DEN001-B2UID006', 'brand': 'Microsoft', 'model': 'Surface 1960', 'grade': 'VG', 'notes': 'very good'},
    {'sku': 'G-DEN001-B2UID007', 'brand': 'Samsung', 'model': 'NP730QDA', 'grade': 'G', 'notes': 'good condition'},
    {'sku': 'VG-DEN001-B2UID010', 'brand': 'Asus', 'model': 'ROG GA401I', 'grade': 'VG', 'notes': 'very good'},
    {'sku': 'LN-DEN001-B2UID011', 'brand': 'Dell', 'model': 'Alienware P69F', 'grade': 'LN', 'notes': 'pristine'},
    {'sku': 'LN-DEN001-B2UID012', 'brand': 'Lenovo', 'model': 'Yoga 6 13ARE05', 'grade': 'LN', 'notes': 'pristine'},
]

print("\n" + "="*100)
print(" AUTOMATED PRICING - B2 BATCH WITH TAVILY WEB SEARCH")
print("="*100 + "\n")

results = []

for item in b2_items:
    sku = item['sku']
    brand = item['brand']
    model = item['model']
    grade = item['grade']
    condition = normalize_condition(grade)

    print(f"\n{'='*100}")
    print(f"  SKU: {sku}")
    print(f"  Product: {brand} {model}")
    print(f"  Condition: {grade} → {condition}")
    print(f"  Notes: {item['notes']}")
    print("-"*100)

    try:
        # Get pricing with Tavily search
        pricing = get_pricing_recommendation(
            brand=brand,
            model=model,
            condition=condition,
            retail_price=None  # Let it find market data
        )

        # Display results
        print(f"\n  💰 PRICING RESULTS:")
        print(f"     Buy-It-Now:      ${pricing.buy_it_now_price:.2f}")

        if pricing.min_offer_price:
            print(f"     Min Offer:       ${pricing.min_offer_price:.2f}")
            print(f"     Auto-Accept:     ${pricing.auto_accept_offer:.2f}")
            print(f"     Auto-Decline:    ${pricing.auto_decline_offer:.2f}")

        if pricing.market_data:
            print(f"\n  📊 MARKET DATA:")
            print(f"     Sold Comps:      {pricing.market_data.sold_count}")

            if pricing.market_data.sold_count > 0:
                print(f"     Avg Sold:        ${pricing.market_data.avg_sold_price:.2f}")
                print(f"     Price Range:     ${pricing.market_data.price_range_low:.2f} - ${pricing.market_data.price_range_high:.2f}")

            print(f"     Active Listings: {pricing.market_data.active_listing_count}")

            if pricing.market_data.sources:
                print(f"     Data Sources:    {', '.join(pricing.market_data.sources)}")

        print(f"\n  📈 CONFIDENCE:")
        print(f"     Score:           {pricing.confidence:.0%}")
        print(f"     Method:          {pricing.reasoning}")

        # Store results
        results.append({
            'sku': sku,
            'brand': brand,
            'model': model,
            'grade': grade,
            'condition': condition,
            'buy_it_now_price': pricing.buy_it_now_price,
            'min_offer': pricing.min_offer_price if pricing.min_offer_price else 0,
            'sold_comps': pricing.market_data.sold_count if pricing.market_data else 0,
            'avg_sold_price': pricing.market_data.avg_sold_price if pricing.market_data else 0,
            'confidence': pricing.confidence,
            'pricing_source': ', '.join(pricing.market_data.sources) if pricing.market_data and pricing.market_data.sources else 'fallback'
        })

    except Exception as e:
        print(f"\n  ❌ ERROR: {e}")
        results.append({
            'sku': sku,
            'brand': brand,
            'model': model,
            'grade': grade,
            'condition': condition,
            'buy_it_now_price': 0,
            'min_offer': 0,
            'sold_comps': 0,
            'avg_sold_price': 0,
            'confidence': 0,
            'pricing_source': 'error'
        })

# Create results DataFrame
results_df = pd.DataFrame(results)

# Save to CSV
output_path = '../data/B2_pricing_with_tavily.csv'
results_df.to_csv(output_path, index=False)

print("\n" + "="*100)
print(" SUMMARY")
print("="*100)

print(f"\nTotal items processed: {len(results)}")
print(f"Results saved to: {output_path}")

# Statistics
items_with_sold_data = results_df[results_df['sold_comps'] > 0]
avg_confidence = results_df['confidence'].mean()

print(f"\nItems with sold comp data: {len(items_with_sold_data)}/{len(results)}")
print(f"Average confidence: {avg_confidence:.0%}")

if len(items_with_sold_data) > 0:
    print(f"\nItems with market data:")
    for _, row in items_with_sold_data.iterrows():
        print(f"  • {row['brand']} {row['model']}: {row['sold_comps']} comps, ${row['avg_sold_price']:.2f} avg")

print("\n" + "="*100)
print("\n✅ Pricing complete! Check the CSV for full results.\n")
