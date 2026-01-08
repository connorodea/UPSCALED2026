#!/usr/bin/env python3
"""
Cache Manager for eBay Pricing

Provides SQLite-based caching for market data to minimize API costs and improve performance.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from ebay_pricing import MarketData, SoldListing
from config import PRICING_CONFIG

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages SQLite cache for market pricing data"""

    def __init__(self, db_path: str = None):
        """Initialize cache manager with SQLite database"""
        if db_path is None:
            # Store in EbayAutolister directory
            base_dir = Path(__file__).parent.parent
            db_path = base_dir / "ebay_pricing_cache.db"

        self.db_path = str(db_path)
        self._init_database()
        logger.info(f"Cache manager initialized: {self.db_path}")

    def _init_database(self):
        """Create database and table if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_cache (
                cache_key TEXT PRIMARY KEY,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                condition TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON market_cache(expires_at)
        """)

        conn.commit()
        conn.close()
        logger.debug("Database initialized successfully")

    def _generate_cache_key(self, brand: str, model: str, condition: str) -> str:
        """Generate consistent cache key from brand, model, condition"""
        # Normalize to lowercase and remove extra whitespace
        brand = ' '.join(brand.lower().split())
        model = ' '.join(model.lower().split())
        condition = condition.lower().strip()

        return f"{brand}_{model}_{condition}"

    def get_cached_market_data(self, brand: str, model: str, condition: str) -> Optional[MarketData]:
        """
        Retrieve cached market data if available and fresh.

        Args:
            brand: Product brand
            model: Product model
            condition: Item condition

        Returns:
            MarketData if found and fresh, None otherwise
        """
        cache_key = self._generate_cache_key(brand, model, condition)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT data_json, created_at, expires_at
            FROM market_cache
            WHERE cache_key = ?
        """, (cache_key,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.debug(f"Cache miss: {cache_key}")
            return None

        data_json, created_at, expires_at = row
        expires_at = datetime.fromisoformat(expires_at)

        # Check if cache entry is still valid
        if datetime.now() > expires_at:
            logger.debug(f"Cache expired: {cache_key}")
            self._delete_cache_entry(cache_key)
            return None

        # Deserialize MarketData from JSON
        try:
            market_data = self._deserialize_market_data(data_json)
            created_at_dt = datetime.fromisoformat(created_at)
            age_hours = (datetime.now() - created_at_dt).total_seconds() / 3600
            market_data.data_age_hours = age_hours

            logger.info(f"Cache hit: {cache_key} (age: {age_hours:.1f}h)")
            return market_data

        except Exception as e:
            logger.error(f"Failed to deserialize cache data: {e}")
            self._delete_cache_entry(cache_key)
            return None

    def cache_market_data(self, market_data: MarketData) -> None:
        """
        Store market data in cache.

        Args:
            market_data: MarketData object to cache
        """
        cache_key = self._generate_cache_key(
            market_data.brand,
            market_data.model,
            market_data.condition
        )

        # Serialize MarketData to JSON
        data_json = self._serialize_market_data(market_data)

        created_at = datetime.now()
        cache_duration = timedelta(hours=PRICING_CONFIG['cache_duration_hours'])
        expires_at = created_at + cache_duration

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use INSERT OR REPLACE to update existing entries
        cursor.execute("""
            INSERT OR REPLACE INTO market_cache
            (cache_key, brand, model, condition, data_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            market_data.brand,
            market_data.model,
            market_data.condition,
            data_json,
            created_at.isoformat(),
            expires_at.isoformat()
        ))

        conn.commit()
        conn.close()

        logger.info(f"Cached market data: {cache_key} (expires: {expires_at.strftime('%Y-%m-%d %H:%M')})")

    def _delete_cache_entry(self, cache_key: str) -> None:
        """Delete a specific cache entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM market_cache WHERE cache_key = ?", (cache_key,))

        conn.commit()
        conn.close()

    def clear_stale_cache(self, max_age_hours: int = None) -> int:
        """
        Remove stale cache entries.

        Args:
            max_age_hours: Override default cache duration (from config if None)

        Returns:
            Number of entries deleted
        """
        if max_age_hours is None:
            max_age_hours = PRICING_CONFIG['cache_duration_hours']

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM market_cache
            WHERE expires_at < ?
        """, (cutoff_time.isoformat(),))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleared {deleted_count} stale cache entries")
        return deleted_count

    def clear_all_cache(self) -> int:
        """
        Clear entire cache.

        Returns:
            Number of entries deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM market_cache")
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        logger.info(f"Cleared all cache ({deleted_count} entries)")
        return deleted_count

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM market_cache")
        total_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM market_cache
            WHERE expires_at >= ?
        """, (datetime.now().isoformat(),))
        valid_count = cursor.fetchone()[0]

        conn.close()

        stale_count = total_count - valid_count

        return {
            'total_entries': total_count,
            'valid_entries': valid_count,
            'stale_entries': stale_count
        }

    def _serialize_market_data(self, market_data: MarketData) -> str:
        """Convert MarketData to JSON string"""
        # Convert sold_listings to dict format
        sold_listings_data = []
        for listing in market_data.sold_listings:
            sold_listings_data.append({
                'title': listing.title,
                'price': listing.price,
                'sold_date': listing.sold_date.isoformat(),
                'condition': listing.condition,
                'source': listing.source,
                'url': listing.url
            })

        data_dict = {
            'brand': market_data.brand,
            'model': market_data.model,
            'condition': market_data.condition,
            'avg_sold_price': market_data.avg_sold_price,
            'median_sold_price': market_data.median_sold_price,
            'price_range_low': market_data.price_range_low,
            'price_range_high': market_data.price_range_high,
            'sold_count': market_data.sold_count,
            'sold_listings': sold_listings_data,
            'active_listing_count': market_data.active_listing_count,
            'avg_active_price': market_data.avg_active_price,
            'median_active_price': market_data.median_active_price,
            'confidence': market_data.confidence,
            'sources': market_data.sources
        }

        return json.dumps(data_dict)

    def _deserialize_market_data(self, data_json: str) -> MarketData:
        """Convert JSON string to MarketData object"""
        data_dict = json.loads(data_json)

        # Convert sold_listings back to SoldListing objects
        sold_listings = []
        for listing_data in data_dict.get('sold_listings', []):
            sold_listings.append(SoldListing(
                title=listing_data['title'],
                price=listing_data['price'],
                sold_date=datetime.fromisoformat(listing_data['sold_date']),
                condition=listing_data['condition'],
                source=listing_data['source'],
                url=listing_data.get('url')
            ))

        return MarketData(
            brand=data_dict['brand'],
            model=data_dict['model'],
            condition=data_dict['condition'],
            avg_sold_price=data_dict.get('avg_sold_price', 0.0),
            median_sold_price=data_dict.get('median_sold_price', 0.0),
            price_range_low=data_dict.get('price_range_low', 0.0),
            price_range_high=data_dict.get('price_range_high', 0.0),
            sold_count=data_dict.get('sold_count', 0),
            sold_listings=sold_listings,
            active_listing_count=data_dict.get('active_listing_count', 0),
            avg_active_price=data_dict.get('avg_active_price', 0.0),
            median_active_price=data_dict.get('median_active_price', 0.0),
            confidence=data_dict.get('confidence', 0.0),
            sources=data_dict.get('sources', [])
        )


# Global cache instance
_cache_instance = None


def get_cache() -> CacheManager:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
