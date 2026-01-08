#!/usr/bin/env python3
"""
Core Pricing Engine

Orchestrates all data sources (AI research, Browse API, cache) and calculates final pricing
using the formula: price = (avg_sold_last_30_days * 0.92) - condition_penalty
"""

import logging
from typing import Optional

from ebay_pricing import MarketData, PricingRecommendation
from ebay_pricing.cache_manager import get_cache
from ebay_pricing.market_research import research_sold_comps_ai, calculate_sold_stats
from ebay_pricing.browse_api import analyze_active_competition
from config import PRICING_CONFIG, BEST_OFFER_CONFIG, CONDITION_MAPPINGS

logger = logging.getLogger(__name__)


def get_pricing_recommendation(brand: str, model: str, condition: str,
                               retail_price: float = None, upc: str = None) -> PricingRecommendation:
    """
    Get intelligent pricing recommendation based on market data.

    Args:
        brand: Product brand
        model: Product model
        condition: Item condition
        retail_price: Original retail price (optional, used for fallback)
        upc: UPC/EAN barcode (optional, enables accurate product lookup)

    Returns:
        PricingRecommendation with all price points
    """
    # Try UPC lookup first for better product data
    product_name = model
    if upc:
        from ebay_pricing.upc_lookup import lookup_product
        upc_data = lookup_product(upc)

        if upc_data:
            logger.info(f"UPC lookup found: {upc_data['title']}")

            # Use full product name for better searches
            if upc_data.get('title'):
                product_name = upc_data['title']

            # Use MSRP from UPC if available and no retail_price provided
            if not retail_price and upc_data.get('msrp'):
                retail_price = upc_data['msrp']
                logger.info(f"Using MSRP from UPC: ${retail_price:.2f}")

            # Update brand if more accurate
            if upc_data.get('brand'):
                brand = upc_data['brand']

    logger.info(f"Calculating pricing for: {brand} {product_name} ({condition})")

    # Normalize condition to eBay standard
    normalized_condition = CONDITION_MAPPINGS.get(condition.lower(), condition).upper()

    # Step 1: Try to get from cache
    cache = get_cache()
    market_data = cache.get_cached_market_data(brand, product_name, normalized_condition)

    # Step 2: If not cached, fetch fresh market data
    if market_data is None:
        logger.info("Cache miss - fetching fresh market data")
        market_data = fetch_market_data(brand, product_name, normalized_condition)

        # Cache the results
        if market_data.sold_count > 0 or market_data.active_listing_count > 0:
            cache.cache_market_data(market_data)
    else:
        logger.info(f"Using cached data (age: {market_data.data_age_hours:.1f}h)")

    # Step 3: Calculate pricing based on market data
    pricing = calculate_pricing_from_market_data(
        market_data,
        normalized_condition,
        retail_price
    )

    logger.info(f"Pricing calculated: ${pricing.buy_it_now_price:.2f} (confidence: {pricing.confidence:.2f})")

    return pricing


def fetch_market_data(brand: str, model: str, condition: str) -> MarketData:
    """
    Fetch fresh market data from all sources.

    Args:
        brand: Product brand
        model: Product model
        condition: Item condition (normalized)

    Returns:
        MarketData object with aggregated intelligence
    """
    market_data = MarketData(
        brand=brand,
        model=model,
        condition=condition,
        sources=[]
    )

    # Fetch sold comps from AI research
    try:
        logger.info("Fetching sold comps from AI research...")
        sold_listings = research_sold_comps_ai(brand, model, condition)

        if sold_listings:
            market_data.sold_listings = sold_listings
            sold_stats = calculate_sold_stats(sold_listings)

            market_data.avg_sold_price = sold_stats['avg_sold_price']
            market_data.median_sold_price = sold_stats['median_sold_price']
            market_data.price_range_low = sold_stats['price_range_low']
            market_data.price_range_high = sold_stats['price_range_high']
            market_data.sold_count = sold_stats['sold_count']
            market_data.sources.append('ai_research')

            logger.info(f"AI research: {market_data.sold_count} sold comps, avg ${market_data.avg_sold_price:.2f}")

    except Exception as e:
        logger.error(f"AI research failed: {e}")

    # Fetch active listings from Browse API
    try:
        logger.info("Fetching active listings from Browse API...")
        active_stats = analyze_active_competition(brand, model, condition)

        if active_stats['active_listing_count'] > 0:
            market_data.avg_active_price = active_stats['avg_active_price']
            market_data.median_active_price = active_stats['median_active_price']
            market_data.active_listing_count = active_stats['active_listing_count']
            market_data.sources.append('browse_api')

            logger.info(f"Browse API: {market_data.active_listing_count} active listings, avg ${market_data.avg_active_price:.2f}")

    except Exception as e:
        logger.error(f"Browse API failed: {e}")

    return market_data


def calculate_pricing_from_market_data(market_data: MarketData, condition: str,
                                      retail_price: Optional[float] = None) -> PricingRecommendation:
    """
    Calculate final pricing from market data.

    Args:
        market_data: MarketData object
        condition: Item condition (normalized)
        retail_price: Original retail price for fallback

    Returns:
        PricingRecommendation object
    """
    config = PRICING_CONFIG
    base_multiplier = config['base_multiplier']
    min_samples = config['min_sold_samples']

    # Determine base price and confidence
    if market_data.sold_count >= min_samples:
        # Use sold comps (highest confidence)
        base_price = market_data.avg_sold_price
        confidence = 0.9
        reasoning = f"Based on {market_data.sold_count} sold listings (avg ${base_price:.2f})"
        logger.info(f"Using sold comps: ${base_price:.2f}")

    elif market_data.active_listing_count > 0:
        # Use active listings * 0.95 (medium confidence)
        base_price = market_data.avg_active_price * 0.95
        confidence = 0.6
        reasoning = f"Based on {market_data.active_listing_count} active listings (${market_data.avg_active_price:.2f} * 0.95)"
        logger.info(f"Using active listings: ${base_price:.2f}")

    elif retail_price and retail_price > 0:
        # Fallback to retail price * 50% (low confidence)
        base_price = retail_price * config['fallback_msrp_multiplier']
        confidence = 0.3
        reasoning = f"Fallback to {config['fallback_msrp_multiplier']*100}% MSRP (${retail_price:.2f})"
        logger.warning(f"Using fallback pricing: ${base_price:.2f}")

    else:
        # No data available
        logger.error("No pricing data available and no retail price provided")
        return PricingRecommendation(
            buy_it_now_price=0.0,
            confidence=0.0,
            reasoning="No market data or retail price available",
            market_data=market_data
        )

    # Apply formula: price = (base_price * 0.92) * (1 - condition_penalty)
    condition_penalty = config['condition_penalties'].get(condition, 0.10)

    # First apply base multiplier, then subtract condition penalty
    price_after_multiplier = base_price * base_multiplier
    buy_it_now_price = price_after_multiplier * (1 - condition_penalty)

    logger.info(f"Pricing calculation: ${base_price:.2f} * {base_multiplier} * (1 - {condition_penalty}) = ${buy_it_now_price:.2f}")

    # Calculate best offer thresholds
    best_offer_config = BEST_OFFER_CONFIG

    if best_offer_config['enabled']:
        min_offer_price = buy_it_now_price * best_offer_config['min_offer_percentage']
        auto_accept_offer = buy_it_now_price * best_offer_config['auto_accept_percentage']
        auto_decline_offer = buy_it_now_price * best_offer_config['auto_decline_percentage']
    else:
        min_offer_price = None
        auto_accept_offer = None
        auto_decline_offer = None

    # Build detailed reasoning
    detailed_reasoning = f"{reasoning}. "
    detailed_reasoning += f"Applied {base_multiplier*100}% base multiplier and {condition_penalty*100}% condition penalty for {condition}. "
    detailed_reasoning += f"Final BIN: ${buy_it_now_price:.2f}"

    return PricingRecommendation(
        buy_it_now_price=buy_it_now_price,
        min_offer_price=min_offer_price,
        auto_accept_offer=auto_accept_offer,
        auto_decline_offer=auto_decline_offer,
        auction_start_price=None,  # Not implementing auction pricing yet
        auction_reserve_price=None,
        confidence=confidence,
        reasoning=detailed_reasoning,
        market_data=market_data
    )


def get_pricing_summary(pricing: PricingRecommendation) -> str:
    """
    Generate a human-readable pricing summary.

    Args:
        pricing: PricingRecommendation object

    Returns:
        Formatted summary string
    """
    summary = f"""
Pricing Summary
===============
Buy It Now:     ${pricing.buy_it_now_price:.2f}
Min Offer:      ${pricing.min_offer_price:.2f if pricing.min_offer_price else 0:.2f}
Auto-Accept:    ${pricing.auto_accept_offer:.2f if pricing.auto_accept_offer else 0:.2f}
Auto-Decline:   ${pricing.auto_decline_offer:.2f if pricing.auto_decline_offer else 0:.2f}

Confidence:     {pricing.confidence:.0%}
Reasoning:      {pricing.reasoning}

Market Data:
- Sold listings:   {pricing.market_data.sold_count if pricing.market_data else 0}
- Active listings: {pricing.market_data.active_listing_count if pricing.market_data else 0}
- Avg sold price:  ${pricing.market_data.avg_sold_price if pricing.market_data else 0:.2f}
- Sources:         {', '.join(pricing.market_data.sources) if pricing.market_data else 'none'}
"""
    return summary.strip()


# Convenience function for backward compatibility
def calculate_price(brand: str, model: str, condition: str,
                   retail_price: float = None) -> float:
    """
    Simple function that returns just the buy-it-now price.

    Args:
        brand: Product brand
        model: Product model
        condition: Item condition
        retail_price: Original retail price

    Returns:
        Buy-it-now price as float
    """
    pricing = get_pricing_recommendation(brand, model, condition, retail_price)
    return pricing.buy_it_now_price
