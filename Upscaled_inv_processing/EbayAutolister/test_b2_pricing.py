#!/usr/bin/env python3
"""
Test automated pricing with real B2 batch data
"""

import os
import sys
import pandas as pd
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ebay_pricing.pricing_engine import get_pricing_recommendation
from config import CONDITION_MAPPINGS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_condition(grade):
    """Normalize grade codes to eBay conditions"""
    grade_map = {
        'LN': 'LIKE_NEW',
        'VG': 'USED_VERY_GOOD',
        'G': 'USED_GOOD',
        'AC': 'USED_ACCEPTABLE',
        'SA': 'FOR_PARTS_OR_NOT_WORKING'
    }
    return grade_map.get(grade.upper(), 'USED_GOOD')


def test_b2_pricing():
    """Test pricing with B2 batch data"""

    # Load CSV
    csv_path = '../data/B2_test.csv'
    df = pd.read_csv(csv_path)

    print("\n" + "="*100)
    print("AUTOMATED PRICING TEST - B2 BATCH DATA")
    print("="*100 + "\n")

    results = []

    for idx, row in df.iterrows():
        sku = row['sku']
        brand = str(row['brand']).strip()
        model = str(row['model']).strip() if pd.notna(row['model']) else ''
        grade = str(row['grade']).strip()

        # Normalize condition
        condition = normalize_condition(grade)

        # Create full product name for better research
        if model:
            product_name = f"{brand} {model}"
        else:
            product_name = brand

        print(f"\n{'='*100}")
        print(f"SKU: {sku}")
        print(f"Product: {product_name}")
        print(f"Condition: {grade} → {condition}")
        print(f"Notes: {row['condition']}")
        print("-"*100)

        try:
            # Get pricing recommendation
            # Note: We don't have retail price, so it will use market data or fallback
            pricing = get_pricing_recommendation(
                brand=brand,
                model=model if model else brand,
                condition=condition,
                retail_price=None  # Will use market data or fallback
            )

            # Display results
            print(f"\n📊 PRICING RESULTS:")
            print(f"   Buy-It-Now Price:    ${pricing.buy_it_now_price:.2f}")
            print(f"   Min Offer:           ${pricing.min_offer_price:.2f if pricing.min_offer_price else 0:.2f}")
            print(f"   Auto-Accept:         ${pricing.auto_accept_offer:.2f if pricing.auto_accept_offer else 0:.2f}")
            print(f"   Auto-Decline:        ${pricing.auto_decline_offer:.2f if pricing.auto_decline_offer else 0:.2f}")

            if pricing.market_data:
                print(f"\n📈 MARKET DATA:")
                print(f"   Sold Comps (30d):    {pricing.market_data.sold_count}")
                print(f"   Avg Sold Price:      ${pricing.market_data.avg_sold_price:.2f}")
                print(f"   Active Listings:     {pricing.market_data.active_listing_count}")
                print(f"   Avg Active Price:    ${pricing.market_data.avg_active_price:.2f}")
                print(f"   Data Sources:        {', '.join(pricing.market_data.sources)}")

            print(f"\n💡 ANALYSIS:")
            print(f"   Confidence:          {pricing.confidence:.0%}")
            print(f"   Reasoning:           {pricing.reasoning}")

            # Store results
            results.append({
                'sku': sku,
                'brand': brand,
                'model': model,
                'condition': condition,
                'buy_it_now_price': pricing.buy_it_now_price,
                'min_offer_price': pricing.min_offer_price if pricing.min_offer_price else 0,
                'avg_sold_price_30d': pricing.market_data.avg_sold_price if pricing.market_data else 0,
                'sold_count_30d': pricing.market_data.sold_count if pricing.market_data else 0,
                'avg_active_price': pricing.market_data.avg_active_price if pricing.market_data else 0,
                'active_listing_count': pricing.market_data.active_listing_count if pricing.market_data else 0,
                'confidence': pricing.confidence,
                'reasoning': pricing.reasoning
            })

        except Exception as e:
            logger.error(f"Pricing failed for {sku}: {e}", exc_info=True)
            print(f"\n❌ ERROR: {e}")

            results.append({
                'sku': sku,
                'brand': brand,
                'model': model,
                'condition': condition,
                'buy_it_now_price': 0,
                'min_offer_price': 0,
                'avg_sold_price_30d': 0,
                'sold_count_30d': 0,
                'avg_active_price': 0,
                'active_listing_count': 0,
                'confidence': 0,
                'reasoning': f'Error: {str(e)}'
            })

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Save results
    output_path = '../data/B2_pricing_results.csv'
    results_df.to_csv(output_path, index=False)

    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    print(f"\nTotal items processed: {len(results)}")
    print(f"Results saved to: {output_path}")

    # Statistics
    avg_confidence = results_df['confidence'].mean()
    items_with_sold_data = (results_df['sold_count_30d'] > 0).sum()
    items_with_active_data = (results_df['active_listing_count'] > 0).sum()

    print(f"\nAverage confidence: {avg_confidence:.0%}")
    print(f"Items with sold comp data: {items_with_sold_data}/{len(results)}")
    print(f"Items with active listing data: {items_with_active_data}/{len(results)}")

    print("\n" + "="*100)
    print("\n✅ Pricing test complete! Check B2_pricing_results.csv for full data.\n")


if __name__ == "__main__":
    test_b2_pricing()
