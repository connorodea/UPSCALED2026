#!/usr/bin/env python3
"""
AI-Powered Market Research for Sold Comps

Uses Tavily API for web search to find recent sold listings and extract pricing data.
"""

import os
import json
import logging
import statistics
import re
from datetime import datetime, timedelta
from typing import List

from tavily import TavilyClient
from openai import OpenAI

from ebay_pricing import SoldListing
from config import PRICING_CONFIG

logger = logging.getLogger(__name__)


def research_sold_comps_ai(brand: str, model: str, condition: str) -> List[SoldListing]:
    """
    Use Tavily web search + OpenAI to find recent sold listings.

    Args:
        brand: Product brand
        model: Product model
        condition: Item condition

    Returns:
        List of SoldListing objects (may be empty if no results found)
    """
    tavily_key = os.getenv("TAVILY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not tavily_key:
        logger.error("TAVILY_API_KEY not set in .env")
        return []

    lookback_days = PRICING_CONFIG['sold_items_lookback_days']

    try:
        # Step 1: Use Tavily to search for eBay sold listings
        logger.info(f"Searching web for sold comps: {brand} {model} ({condition})")

        tavily = TavilyClient(api_key=tavily_key)

        # Construct search query for eBay sold items
        search_query = f"{brand} {model} sold ebay completed listings price"

        # Search with Tavily
        search_results = tavily.search(
            query=search_query,
            search_depth="advanced",  # More comprehensive search
            max_results=10,
            include_domains=["ebay.com"],  # Focus on eBay
        )

        logger.info(f"Tavily found {len(search_results.get('results', []))} search results")

        if not search_results.get('results'):
            logger.warning(f"No web results found for {brand} {model}")
            return []

        # Step 2: Use OpenAI to extract pricing data from search results
        if not openai_key:
            logger.warning("OPENAI_API_KEY not set, using basic parsing")
            return _parse_results_basic(search_results, brand, model, condition, lookback_days)

        return _parse_results_with_ai(search_results, brand, model, condition, lookback_days)

    except Exception as e:
        logger.error(f"Tavily market research failed: {e}")
        return []


def _parse_results_with_ai(search_results: dict, brand: str, model: str,
                           condition: str, lookback_days: int) -> List[SoldListing]:
    """Use OpenAI to intelligently parse search results and extract pricing data"""

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Compile search results into context
    context = "eBay Search Results:\n\n"
    for idx, result in enumerate(search_results.get('results', [])[:10], 1):
        context += f"{idx}. {result.get('title', 'No title')}\n"
        context += f"   URL: {result.get('url', 'No URL')}\n"
        context += f"   Content: {result.get('content', 'No content')[:300]}...\n\n"

    # Ask OpenAI to extract pricing data
    prompt = f"""
Extract pricing data from these eBay search results for "{brand} {model}".

{context}

Look for prices in the content (like $419.64, $344.99, $95.00, etc.) and extract them.

Return JSON with this EXACT format:
{{
  "listings": [
    {{
      "title": "Product title from search",
      "price": 419.64,
      "sold_date": "2024-12-01",
      "condition": "Used - Very Good",
      "url": "URL from search"
    }}
  ]
}}

RULES:
- Extract ANY price you see (from bids, Buy It Now, or sold items)
- Use prices between $50-$3000 (reasonable laptop/device range)
- If you see "\X sold" or bids, those are legitimate data points
- Include "Pre-Owned" or "Refurbished" items
- Put today's date if sold date unknown
- Extract 3-10 listings if available
- If NO prices found, return empty listings array []
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content
        result_data = json.loads(result_text)

        listings_data = result_data.get('listings', [])

        # Convert to SoldListing objects
        sold_listings = []
        cutoff_date = datetime.now() - timedelta(days=lookback_days)

        for listing_data in listings_data:
            try:
                price = float(listing_data.get('price', 0))
                if price <= 0:
                    continue

                # Parse date
                date_str = listing_data.get('sold_date', '')
                try:
                    sold_date = datetime.fromisoformat(date_str.replace('Z', ''))
                except:
                    sold_date = datetime.now()  # Assume recent

                # Filter by date
                if sold_date < cutoff_date:
                    continue

                sold_listing = SoldListing(
                    title=listing_data.get('title', f"{brand} {model}"),
                    price=price,
                    sold_date=sold_date,
                    condition=listing_data.get('condition', condition),
                    source='tavily_ai',
                    url=listing_data.get('url')
                )

                sold_listings.append(sold_listing)

            except Exception as e:
                logger.warning(f"Failed to parse listing: {e}")
                continue

        logger.info(f"Extracted {len(sold_listings)} sold listings from AI analysis")
        return sold_listings

    except Exception as e:
        logger.error(f"AI parsing failed: {e}")
        return []


def _parse_results_basic(search_results: dict, brand: str, model: str,
                         condition: str, lookback_days: int) -> List[SoldListing]:
    """Basic parsing without AI - extract prices using regex"""

    sold_listings = []

    # Price regex patterns
    price_patterns = [
        r'\$(\d+\.?\d*)',  # $299.99
        r'(\d+\.?\d*)\s*USD',  # 299.99 USD
        r'sold for \$?(\d+\.?\d*)',  # sold for $299
    ]

    for result in search_results.get('results', [])[:10]:
        content = result.get('content', '') + ' ' + result.get('title', '')
        url = result.get('url', '')

        # Only process if it looks like a sold listing
        if 'sold' not in content.lower():
            continue

        # Extract price
        price = None
        for pattern in price_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    if 10 <= price <= 10000:  # Reasonable price range
                        break
                except:
                    continue

        if not price:
            continue

        sold_listing = SoldListing(
            title=result.get('title', f"{brand} {model}")[:100],
            price=price,
            sold_date=datetime.now(),  # Assume recent
            condition=condition,
            source='tavily_basic',
            url=url
        )

        sold_listings.append(sold_listing)

    logger.info(f"Extracted {len(sold_listings)} sold listings from basic parsing")
    return sold_listings


def remove_outliers(prices: List[float], threshold: float = None) -> List[float]:
    """
    Remove statistical outliers using Z-score method.

    Args:
        prices: List of prices
        threshold: Z-score threshold (from config if None)

    Returns:
        Filtered list of prices with outliers removed
    """
    if threshold is None:
        threshold = PRICING_CONFIG['outlier_threshold']

    if len(prices) < 3:
        return prices

    try:
        mean = statistics.mean(prices)
        stdev = statistics.stdev(prices)

        if stdev == 0:
            return prices

        # Calculate Z-scores and filter
        filtered_prices = []
        outliers_removed = 0

        for price in prices:
            z_score = abs((price - mean) / stdev)
            if z_score <= threshold:
                filtered_prices.append(price)
            else:
                logger.debug(f"Removed outlier: ${price:.2f} (z-score: {z_score:.2f})")
                outliers_removed += 1

        # If we removed everything, keep median
        if not filtered_prices:
            median_price = statistics.median(prices)
            filtered_prices = [median_price]
            logger.warning("All prices were outliers, keeping median")

        if outliers_removed > 0:
            logger.info(f"Removed {outliers_removed} price outliers")

        return filtered_prices

    except Exception as e:
        logger.error(f"Outlier removal failed: {e}")
        return prices


def calculate_sold_stats(sold_listings: List[SoldListing]) -> dict:
    """
    Calculate statistics from sold listings.

    Args:
        sold_listings: List of SoldListing objects

    Returns:
        Dictionary with avg, median, range, count
    """
    if not sold_listings:
        return {
            'avg_sold_price': 0.0,
            'median_sold_price': 0.0,
            'price_range_low': 0.0,
            'price_range_high': 0.0,
            'sold_count': 0
        }

    # Extract prices
    prices = [listing.price for listing in sold_listings]

    # Remove outliers
    filtered_prices = remove_outliers(prices)

    # Calculate statistics
    avg_price = statistics.mean(filtered_prices)
    median_price = statistics.median(filtered_prices)
    min_price = min(filtered_prices)
    max_price = max(filtered_prices)

    return {
        'avg_sold_price': avg_price,
        'median_sold_price': median_price,
        'price_range_low': min_price,
        'price_range_high': max_price,
        'sold_count': len(sold_listings)
    }
