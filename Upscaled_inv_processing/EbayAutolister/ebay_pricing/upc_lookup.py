#!/usr/bin/env python3
"""
UPC Product Lookup

Uses UPC codes to get accurate product information and retail prices.
Supports multiple free/paid APIs with fallbacks.
"""

import os
import logging
import requests
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UPCLookup:
    """Lookup product information using UPC/EAN codes"""

    def __init__(self):
        """Initialize with API keys from environment"""
        self.upcitemdb_key = os.getenv("UPCITEMDB_API_KEY")
        self.barcodelookup_key = os.getenv("BARCODELOOKUP_API_KEY")
        self.cache = {}  # In-memory cache for session

    def lookup(self, upc: str) -> Optional[Dict]:
        """
        Lookup product by UPC code.

        Tries multiple services in order:
        1. Cache
        2. UPCitemdb (free tier: 100/day)
        3. Barcode Lookup (paid: 500/day)
        4. OpenFoodFacts (free, groceries only)

        Args:
            upc: UPC/EAN barcode (digits only)

        Returns:
            Dictionary with product info or None if not found
        """
        if not upc or not upc.strip():
            return None

        # Clean UPC (remove dashes, spaces)
        upc = ''.join(filter(str.isdigit, str(upc)))

        if not upc:
            return None

        # Check cache first
        if upc in self.cache:
            logger.debug(f"UPC cache hit: {upc}")
            return self.cache[upc]

        # Try UPCitemdb first (free)
        result = self._try_upcitemdb(upc)
        if result:
            self.cache[upc] = result
            return result

        # Try Barcode Lookup (paid)
        result = self._try_barcodelookup(upc)
        if result:
            self.cache[upc] = result
            return result

        # Try OpenFoodFacts (free, but limited to food/consumer goods)
        result = self._try_openfoodfacts(upc)
        if result:
            self.cache[upc] = result
            return result

        logger.warning(f"UPC not found in any database: {upc}")
        return None

    def _try_upcitemdb(self, upc: str) -> Optional[Dict]:
        """
        Try UPCitemdb API
        Free tier: 100 requests/day
        https://www.upcitemdb.com/api/explorer
        """
        if not self.upcitemdb_key:
            logger.debug("UPCitemdb API key not configured")
            return None

        try:
            url = f"https://api.upcitemdb.com/prod/trial/lookup"
            params = {'upc': upc}
            headers = {
                'Accept': 'application/json',
                'user_key': self.upcitemdb_key
            }

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()

                if data.get('items') and len(data['items']) > 0:
                    item = data['items'][0]

                    result = {
                        'title': item.get('title', ''),
                        'brand': item.get('brand', ''),
                        'model': item.get('model', ''),
                        'category': item.get('category', ''),
                        'upc': upc,
                        'msrp': self._parse_price(item.get('msrp')),
                        'lowest_price': self._parse_price(item.get('lowest_recorded_price')),
                        'highest_price': self._parse_price(item.get('highest_recorded_price')),
                        'description': item.get('description', ''),
                        'images': item.get('images', []),
                        'source': 'upcitemdb'
                    }

                    logger.info(f"UPCitemdb found: {result['title']}")
                    return result

            elif response.status_code == 404:
                logger.debug(f"UPC not found in UPCitemdb: {upc}")
            else:
                logger.warning(f"UPCitemdb API error {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"UPCitemdb lookup failed: {e}")

        return None

    def _try_barcodelookup(self, upc: str) -> Optional[Dict]:
        """
        Try Barcode Lookup API
        Paid: $20/month for 500/day
        https://www.barcodelookup.com/api
        """
        if not self.barcodelookup_key:
            logger.debug("Barcode Lookup API key not configured")
            return None

        try:
            url = f"https://api.barcodelookup.com/v3/products"
            params = {
                'barcode': upc,
                'key': self.barcodelookup_key
            }

            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()

                if data.get('products') and len(data['products']) > 0:
                    product = data['products'][0]

                    result = {
                        'title': product.get('title', ''),
                        'brand': product.get('brand', ''),
                        'model': product.get('model', ''),
                        'category': product.get('category', ''),
                        'upc': upc,
                        'msrp': self._parse_price(product.get('msrp')),
                        'description': product.get('description', ''),
                        'images': product.get('images', []),
                        'source': 'barcodelookup'
                    }

                    logger.info(f"Barcode Lookup found: {result['title']}")
                    return result

        except Exception as e:
            logger.error(f"Barcode Lookup failed: {e}")

        return None

    def _try_openfoodfacts(self, upc: str) -> Optional[Dict]:
        """
        Try OpenFoodFacts API
        Free, but mainly for food/consumer goods
        https://world.openfoodfacts.org/api/v0/product/{barcode}.json
        """
        try:
            url = f"https://world.openfoodfacts.org/api/v0/product/{upc}.json"

            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 1 and data.get('product'):
                    product = data['product']

                    result = {
                        'title': product.get('product_name', ''),
                        'brand': product.get('brands', ''),
                        'model': '',
                        'category': product.get('categories', ''),
                        'upc': upc,
                        'msrp': None,  # OpenFoodFacts doesn't have prices
                        'description': product.get('generic_name', ''),
                        'images': [product.get('image_url', '')] if product.get('image_url') else [],
                        'source': 'openfoodfacts'
                    }

                    logger.info(f"OpenFoodFacts found: {result['title']}")
                    return result

        except Exception as e:
            logger.error(f"OpenFoodFacts lookup failed: {e}")

        return None

    def _parse_price(self, price_str) -> Optional[float]:
        """Parse price string to float"""
        if not price_str:
            return None

        try:
            # Remove currency symbols and commas
            price_clean = str(price_str).replace('$', '').replace(',', '').strip()
            return float(price_clean) if price_clean else None
        except:
            return None


# Global instance
_upc_lookup = None


def get_upc_lookup() -> UPCLookup:
    """Get or create global UPC lookup instance"""
    global _upc_lookup
    if _upc_lookup is None:
        _upc_lookup = UPCLookup()
    return _upc_lookup


def lookup_product(upc: str) -> Optional[Dict]:
    """
    Convenience function to lookup product by UPC.

    Returns:
        {
            'title': 'Apple MacBook Air M1 13.3" 2020',
            'brand': 'Apple',
            'model': 'MGN63LL/A',
            'category': 'Computers',
            'msrp': 999.00,
            'upc': '194252056...',
            'source': 'upcitemdb'
        }
    """
    lookup_service = get_upc_lookup()
    return lookup_service.lookup(upc)
