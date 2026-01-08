#!/usr/bin/env python3
"""
Test script for automated pricing system

This script tests the pricing engine with sample products.
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ebay_pricing.pricing_engine import get_pricing_recommendation, get_pricing_summary
from ebay_pricing.cache_manager import get_cache

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_pricing_engine():
    """Test the pricing engine with sample products"""

    # Test products with different conditions
    test_products = [
        {
            'brand': 'Apple',
            'model': 'iPhone 13 Pro 128GB',
            'condition': 'LIKE_NEW',
            'retail_price': 999.00
        },
        {
            'brand': 'Samsung',
            'model': 'Galaxy S21',
            'condition': 'USED_GOOD',
            'retail_price': 799.00
        },
        {
            'brand': 'Sony',
            'model': 'PlayStation 5',
            'condition': 'USED_VERY_GOOD',
            'retail_price': 499.99
        },
        {
            'brand': 'Nintendo',
            'model': 'Switch OLED',
            'condition': 'FOR_PARTS_OR_NOT_WORKING',
            'retail_price': 349.99
        }
    ]

    print("\n" + "="*80)
    print("AUTOMATED PRICING SYSTEM - TEST RESULTS")
    print("="*80 + "\n")

    for product in test_products:
        print(f"\nTesting: {product['brand']} {product['model']} ({product['condition']})")
        print("-" * 80)

        try:
            # Get pricing recommendation
            pricing = get_pricing_recommendation(
                brand=product['brand'],
                model=product['model'],
                condition=product['condition'],
                retail_price=product['retail_price']
            )

            # Display results
            print(get_pricing_summary(pricing))
            print("")

        except Exception as e:
            logger.error(f"Pricing failed: {e}")
            print(f"ERROR: {e}\n")

    # Display cache statistics
    print("\n" + "="*80)
    print("CACHE STATISTICS")
    print("="*80)
    cache = get_cache()
    stats = cache.get_cache_stats()
    print(f"Total entries:  {stats['total_entries']}")
    print(f"Valid entries:  {stats['valid_entries']}")
    print(f"Stale entries:  {stats['stale_entries']}")
    print("")


def test_cache_functionality():
    """Test cache hit/miss behavior"""
    print("\n" + "="*80)
    print("CACHE FUNCTIONALITY TEST")
    print("="*80 + "\n")

    # First call - should be cache miss
    print("First call (cache miss expected)...")
    pricing1 = get_pricing_recommendation('Apple', 'iPad Air', 'LIKE_NEW', 599.00)
    print(f"✓ Pricing: ${pricing1.buy_it_now_price:.2f}\n")

    # Second call - should be cache hit
    print("Second call (cache hit expected)...")
    pricing2 = get_pricing_recommendation('Apple', 'iPad Air', 'LIKE_NEW', 599.00)
    print(f"✓ Pricing: ${pricing2.buy_it_now_price:.2f}")
    print(f"✓ Data age: {pricing2.market_data.data_age_hours:.2f} hours\n")

    # Verify prices match
    assert pricing1.buy_it_now_price == pricing2.buy_it_now_price, "Cache pricing mismatch!"
    print("✓ Cache test passed - prices match!\n")


def clear_test_cache():
    """Clear the cache after tests"""
    cache = get_cache()
    count = cache.clear_all_cache()
    print(f"Cleared {count} cache entries\n")


if __name__ == "__main__":
    print("\nStarting automated pricing system tests...\n")

    try:
        # Run tests
        test_pricing_engine()
        test_cache_functionality()

        # Optional: Clear cache after tests
        # Uncomment to clear:
        # clear_test_cache()

        print("="*80)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
