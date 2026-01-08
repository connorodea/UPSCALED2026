#!/usr/bin/env python3
"""
Simple test with manual retail prices to demonstrate pricing logic
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ebay_pricing.pricing_engine import get_pricing_recommendation

# Test with known products and estimated retail prices
test_products = [
    {'brand': 'Apple', 'model': 'MacBook Air M1', 'condition': 'LIKE_NEW', 'retail': 999.00},
    {'brand': 'Lenovo', 'model': 'Yoga 6', 'condition': 'LIKE_NEW', 'retail': 699.00},
    {'brand': 'Microsoft', 'model': 'Surface Go 2', 'condition': 'USED_VERY_GOOD', 'retail': 399.00},
    {'brand': 'Dell', 'model': 'Alienware M15', 'condition': 'LIKE_NEW', 'retail': 1499.00},
    {'brand': 'Samsung', 'model': 'Galaxy Book', 'condition': 'USED_GOOD', 'retail': 549.00},
]

print("\n" + "="*80)
print("AUTOMATED PRICING DEMONSTRATION - With Retail Fallback")
print("="*80 + "\n")

for product in test_products:
    print(f"\nProduct: {product['brand']} {product['model']}")
    print(f"Condition: {product['condition']}")
    print(f"Retail Price: ${product['retail']:.2f}")
    print("-" * 80)

    pricing = get_pricing_recommendation(
        brand=product['brand'],
        model=product['model'],
        condition=product['condition'],
        retail_price=product['retail']
    )

    print(f"\n  📊 CALCULATED PRICES:")
    print(f"     Buy-It-Now:     ${pricing.buy_it_now_price:.2f}")

    if pricing.min_offer_price:
        print(f"     Min Offer:      ${pricing.min_offer_price:.2f}")
        print(f"     Auto-Accept:    ${pricing.auto_accept_offer:.2f}")
        print(f"     Auto-Decline:   ${pricing.auto_decline_offer:.2f}")

    print(f"\n  💡 PRICING INFO:")
    print(f"     Confidence:     {pricing.confidence:.0%}")
    print(f"     Method:         {pricing.reasoning[:80]}...")
    print("")

print("="*80)
print("PRICING FORMULA DEMONSTRATION")
print("="*80)
print("\nCondition Adjustments Applied:")
print("  - Like New:      0% penalty  → Base price * 0.92 * 1.00")
print("  - Very Good:    10% penalty  → Base price * 0.92 * 0.90")
print("  - Good:         10% penalty  → Base price * 0.92 * 0.90")
print("  - Acceptable:   20% penalty  → Base price * 0.92 * 0.80")
print("  - For Parts:    50% penalty  → Base price * 0.92 * 0.50")
print("\nBest Offer Settings:")
print("  - Min Offer:     85% of Buy-It-Now")
print("  - Auto-Accept:   95% of Buy-It-Now")
print("  - Auto-Decline:  75% of Buy-It-Now")
print("\n" + "="*80 + "\n")
