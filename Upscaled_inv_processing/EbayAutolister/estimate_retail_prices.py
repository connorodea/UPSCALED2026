#!/usr/bin/env python3
"""
Estimate retail prices for B2 batch based on brand/model patterns
Then run automated pricing
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

def estimate_retail_price(brand: str, model: str) -> float:
    """Estimate retail price based on brand and model patterns"""

    brand_lower = brand.lower()
    model_lower = model.lower()

    # Apple products
    if 'apple' in brand_lower:
        if 'a2449' in model_lower or 'macbook' in model_lower:
            return 999.00  # MacBook Air M1
        elif 'a1347' in model_lower:
            return 499.00  # Mac Mini
        else:
            return 799.00  # Default Apple device

    # Microsoft Surface
    elif 'microsoft' in brand_lower and ('surface' in model_lower or '1866' in model_lower or '1960' in model_lower or '1901' in model_lower or '1943' in model_lower):
        if 'pro' in model_lower or '1866' in model_lower or '1796' in model_lower:
            return 899.00  # Surface Pro
        elif 'go' in model_lower or '1960' in model_lower:
            return 399.00  # Surface Go
        elif 'laptop' in model_lower or '1943' in model_lower or '1901' in model_lower:
            return 799.00  # Surface Laptop
        else:
            return 699.00  # Default Surface

    # Lenovo
    elif 'lenovo' in brand_lower:
        if 'yoga' in model_lower:
            if '9' in model_lower:
                return 1199.00  # Yoga 9
            else:
                return 699.00  # Yoga 6/7
        elif 'ideapad' in model_lower:
            return 549.00
        elif 'thinkpad' in model_lower:
            return 899.00
        else:
            return 599.00

    # Dell
    elif 'dell' in brand_lower:
        if 'alienware' in brand_lower or 'alienware' in model_lower:
            return 1499.00  # Gaming laptop
        elif 'xps' in model_lower:
            return 1299.00
        elif 'inspiron' in model_lower:
            return 649.00
        else:
            return 699.00

    # Asus
    elif 'asus' in brand_lower:
        if 'rog' in model_lower or 'gaming' in model_lower:
            return 1199.00  # ROG gaming
        elif 'zenbook' in model_lower:
            return 899.00
        elif 'vivobook' in model_lower:
            return 649.00
        else:
            return 699.00

    # Samsung
    elif 'samsung' in brand_lower:
        if 'galaxy book' in model_lower or 'np730' in model_lower or 'np750' in model_lower:
            return 799.00
        elif 'chromebook' in model_lower:
            return 399.00
        else:
            return 649.00

    # HP
    elif 'hp' in brand_lower:
        if 'spectre' in model_lower:
            return 1199.00
        elif 'envy' in model_lower:
            return 849.00
        elif 'pavilion' in model_lower:
            return 649.00
        else:
            return 549.00

    # Acer
    elif 'acer' in brand_lower:
        if 'predator' in model_lower:
            return 1299.00
        elif 'swift' in model_lower:
            return 799.00
        else:
            return 549.00

    # MSI
    elif 'msi' in brand_lower:
        return 1299.00  # Gaming laptops

    # Nintendo
    elif 'nintendo' in brand_lower:
        if 'switch' in model_lower:
            return 349.99
        else:
            return 299.00

    # Default
    else:
        return 699.00  # Generic laptop/device

# B2 Batch
b2_items = [
    {'sku': 'LN-DEN001-B2UID001', 'brand': 'Apple', 'model': 'A2449', 'grade': 'LN'},
    {'sku': 'VG-DEN001-B2UID002', 'brand': 'APPLE', 'model': 'A1347', 'grade': 'VG'},
    {'sku': 'LN-DEN001-B2UID003', 'brand': 'Nintendo', 'model': 'Switch', 'grade': 'LN'},
    {'sku': 'VG-DEN001-B2UID004', 'brand': 'Apple', 'model': 'A1347', 'grade': 'VG'},
    {'sku': 'LN-DEN001-B2UID005', 'brand': 'Microsoft', 'model': 'Surface 1866', 'grade': 'LN'},
    {'sku': 'VG-DEN001-B2UID006', 'brand': 'Microsoft', 'model': 'Surface 1960', 'grade': 'VG'},
    {'sku': 'G-DEN001-B2UID007', 'brand': 'Samsung', 'model': 'NP730QDA Galaxy Book', 'grade': 'G'},
    {'sku': 'G-DEN001-B2UID008', 'brand': 'HP', 'model': '14-ds0023dx', 'grade': 'G'},
    {'sku': 'VG-DEN001-B2UID009', 'brand': 'HP', 'model': '15m-cn0012dx', 'grade': 'VG'},
    {'sku': 'VG-DEN001-B2UID010', 'brand': 'Asus', 'model': 'ROG GA401I', 'grade': 'VG'},
    {'sku': 'LN-DEN001-B2UID011', 'brand': 'Dell Alienware', 'model': 'P69F', 'grade': 'LN'},
    {'sku': 'LN-DEN001-B2UID012', 'brand': 'LENOVO', 'model': 'Yoga 6 13ARE05', 'grade': 'LN'},
    {'sku': 'VG-DEN001-B2UID013', 'brand': 'Microsoft', 'model': 'Surface 1943', 'grade': 'VG'},
    {'sku': 'VG-DEN001-B2UID014', 'brand': 'LENOVO', 'model': '81W2 IdeaPad', 'grade': 'VG'},
    {'sku': 'VG-DEN001-B2UID015', 'brand': 'Samsung', 'model': 'XE521QAB Chromebook', 'grade': 'VG'},
    {'sku': 'LN-DEN001-B2UID016', 'brand': 'MSI', 'model': 'MS-16V2 Gaming', 'grade': 'LN'},
    {'sku': 'VG-DEN001-B2UID017', 'brand': 'Lenovo', 'model': '81W0 IdeaPad', 'grade': 'VG'},
    {'sku': 'LN-DEN001-B2UID018', 'brand': 'Microsoft', 'model': 'Surface 1901', 'grade': 'LN'},
    {'sku': 'LN-DEN001-B2UID019', 'brand': 'Lenovo', 'model': 'Yoga 9 15IMH5', 'grade': 'LN'},
    {'sku': 'LN-DEN001-B2UID020', 'brand': 'Lenovo', 'model': 'C940-14IIL Yoga', 'grade': 'LN'},
    {'sku': 'LN-DEN001-B2UID021', 'brand': 'ASUS', 'model': 'C433T Chromebook', 'grade': 'LN'},
    {'sku': 'LN-DEN001-B2UID022', 'brand': 'Samsung', 'model': 'NP750TDA Galaxy Book', 'grade': 'LN'},
    {'sku': 'VG-DEN001-B2UID023', 'brand': 'LENOVO', 'model': '80V4 IdeaPad', 'grade': 'VG'},
    {'sku': 'G-DEN001-B2UID024', 'brand': 'ACER', 'model': 'Z5WAH Chromebook', 'grade': 'G'},
    {'sku': 'VG-DEN001-B2UID025', 'brand': 'SAMSUNG', 'model': 'NP730QDA Galaxy Book', 'grade': 'VG'},
]

print("\n" + "="*100)
print(" B2 BATCH AUTOMATED PRICING WITH RETAIL ESTIMATION")
print("="*100 + "\n")

results = []

for item in b2_items:
    sku = item['sku']
    brand = item['brand']
    model = item['model']
    grade = item['grade']
    condition = normalize_condition(grade)

    # Estimate retail price
    retail_price = estimate_retail_price(brand, model)

    # Get automated pricing
    pricing = get_pricing_recommendation(brand, model, condition, retail_price)

    print(f"{sku:<30} {brand:<20} {model:<30} {grade:>2} → ${pricing.buy_it_now_price:>7.2f} BIN  (retail: ${retail_price:>7.2f}, conf: {pricing.confidence:.0%})")

    results.append({
        'sku': sku,
        'brand': brand,
        'model': model,
        'grade': grade,
        'condition': condition,
        'estimated_retail': retail_price,
        'buy_it_now_price': pricing.buy_it_now_price,
        'min_offer': pricing.min_offer_price if pricing.min_offer_price else 0,
        'auto_accept': pricing.auto_accept_offer if pricing.auto_accept_offer else 0,
        'auto_decline': pricing.auto_decline_offer if pricing.auto_decline_offer else 0,
        'confidence': pricing.confidence,
        'pricing_source': pricing.reasoning[:50]
    })

# Save results
results_df = pd.DataFrame(results)
output_path = '../data/B2_final_pricing.csv'
results_df.to_csv(output_path, index=False)

print("\n" + "="*100)
print(" SUMMARY")
print("="*100)
print(f"\nTotal items priced: {len(results)}")
print(f"Results saved to: {output_path}")
print(f"\nAverage BIN price: ${results_df['buy_it_now_price'].mean():.2f}")
print(f"Price range: ${results_df['buy_it_now_price'].min():.2f} - ${results_df['buy_it_now_price'].max():.2f}")
print(f"\n✅ Your B2 batch is priced and ready!\n")
