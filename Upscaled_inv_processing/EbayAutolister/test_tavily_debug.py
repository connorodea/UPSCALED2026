#!/usr/bin/env python3
"""
Debug Tavily integration - see what it's finding
"""

import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Test with a well-known product
test_products = [
    "Apple MacBook Air M1 sold ebay",
    "Microsoft Surface Pro 7 sold ebay",
    "Lenovo Yoga 6 sold ebay",
]

for product in test_products:
    print(f"\n{'='*80}")
    print(f"Searching: {product}")
    print("-"*80)

    results = tavily.search(
        query=product,
        search_depth="advanced",
        max_results=5,
        include_domains=["ebay.com"]
    )

    print(f"\nFound {len(results.get('results', []))} results:\n")

    for idx, result in enumerate(results.get('results', [])[:5], 1):
        print(f"{idx}. {result.get('title', 'No title')}")
        print(f"   URL: {result.get('url', 'No URL')}")
        print(f"   Content preview: {result.get('content', 'No content')[:200]}...")
        print()

print("\n" + "="*80)
print("Analysis: Check if results contain sold listing prices")
print("="*80 + "\n")
