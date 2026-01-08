#!/usr/bin/env python3
"""
eBay Pricing Module - Data Models

Defines core data structures for market research and pricing recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class SoldListing:
    """Represents a single sold listing from market research"""
    title: str
    price: float
    sold_date: datetime
    condition: str
    source: str  # 'ai_research', 'marketplace_insights', etc.
    url: Optional[str] = None

    def __repr__(self):
        return f"SoldListing(price=${self.price:.2f}, date={self.sold_date.date()}, condition={self.condition})"


@dataclass
class MarketData:
    """Aggregated market intelligence for a product"""
    brand: str
    model: str
    condition: str

    # Sold listings data
    avg_sold_price: float = 0.0
    median_sold_price: float = 0.0
    price_range_low: float = 0.0
    price_range_high: float = 0.0
    sold_count: int = 0
    sold_listings: List[SoldListing] = field(default_factory=list)

    # Active listings data
    active_listing_count: int = 0
    avg_active_price: float = 0.0
    median_active_price: float = 0.0

    # Metadata
    confidence: float = 0.0  # 0.0-1.0 confidence score
    data_age_hours: float = 0.0
    sources: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __repr__(self):
        return (f"MarketData({self.brand} {self.model}, "
                f"avg_sold=${self.avg_sold_price:.2f}, "
                f"sold_count={self.sold_count}, "
                f"confidence={self.confidence:.2f})")


@dataclass
class PricingRecommendation:
    """Final pricing recommendation with all price points"""
    # Primary pricing
    buy_it_now_price: float

    # Best offer settings
    min_offer_price: Optional[float] = None
    auto_accept_offer: Optional[float] = None
    auto_decline_offer: Optional[float] = None

    # Auction settings (if using auction format)
    auction_start_price: Optional[float] = None
    auction_reserve_price: Optional[float] = None

    # Metadata
    confidence: float = 0.0  # 0.0-1.0 confidence in this pricing
    reasoning: str = ""  # Explanation of how price was calculated
    market_data: Optional[MarketData] = None

    def __repr__(self):
        return (f"PricingRecommendation(BIN=${self.buy_it_now_price:.2f}, "
                f"min_offer=${self.min_offer_price:.2f if self.min_offer_price else 0:.2f}, "
                f"confidence={self.confidence:.2f})")


__all__ = [
    'SoldListing',
    'MarketData',
    'PricingRecommendation'
]
