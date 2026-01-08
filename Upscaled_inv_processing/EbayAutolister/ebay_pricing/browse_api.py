#!/usr/bin/env python3
"""
eBay Browse API Integration for Active Listing Analysis

Uses eBay Browse API to query current active listings and analyze competitive pricing.
"""

import os
import time
import logging
import statistics
import requests
import base64
from typing import Dict, Any, List
from config import CONDITION_MAPPINGS

logger = logging.getLogger(__name__)


class EbayBrowseAPI:
    """Client for eBay Browse API"""

    # eBay condition IDs mapping
    CONDITION_IDS = {
        'NEW': '1000',
        'LIKE_NEW': '1500',
        'NEW_OTHER': '1750',
        'NEW_WITH_DEFECTS': '2000',
        'CERTIFIED_REFURBISHED': '2000',
        'EXCELLENT_REFURBISHED': '2010',
        'VERY_GOOD_REFURBISHED': '2020',
        'GOOD_REFURBISHED': '2030',
        'SELLER_REFURBISHED': '2500',
        'USED_EXCELLENT': '3000',
        'USED_VERY_GOOD': '4000',
        'USED_GOOD': '5000',
        'USED_ACCEPTABLE': '6000',
        'FOR_PARTS_OR_NOT_WORKING': '7000'
    }

    def __init__(self):
        """Initialize eBay Browse API client"""
        self.client_id = os.getenv('EBAY_CLIENT_ID', '')
        self.client_secret = os.getenv('EBAY_CLIENT_SECRET', '')
        self.sandbox = os.getenv('EBAY_SANDBOX', 'false').lower() == 'true'

        # Set API URLs
        if self.sandbox:
            self.oauth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
            self.base_url = "https://api.sandbox.ebay.com/buy/browse/v1"
        else:
            self.oauth_url = "https://api.ebay.com/identity/v1/oauth2/token"
            self.base_url = "https://api.ebay.com/buy/browse/v1"

        self.access_token = None
        self.token_expires_at = 0
        self.min_interval = 0.1  # 100ms between requests (rate limiting)
        self.last_request_time = 0

    def _get_auth_header(self) -> str:
        """Generate base64 encoded auth header"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return encoded

    def authenticate(self) -> bool:
        """
        Authenticate with eBay OAuth.

        Returns:
            True if authentication successful
        """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {self._get_auth_header()}'
        }

        data = {
            'grant_type': 'client_credentials',
            'scope': 'https://api.ebay.com/oauth/api_scope'
        }

        try:
            response = requests.post(self.oauth_url, headers=headers, data=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            self.access_token = result.get('access_token')
            expires_in = result.get('expires_in', 7200)
            self.token_expires_at = time.time() + expires_in

            logger.info("eBay Browse API authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"eBay Browse API authentication failed: {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid access token"""
        if not self.access_token or time.time() >= self.token_expires_at - 60:
            return self.authenticate()
        return True

    def _rate_limit(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make authenticated request to eBay Browse API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response JSON as dictionary
        """
        if not self._ensure_authenticated():
            raise Exception("Failed to authenticate with eBay API")

        self._rate_limit()

        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"eBay API request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def search_active_listings(self, brand: str, model: str, condition: str = None,
                               limit: int = 50, min_price: float = None,
                               max_price: float = None) -> Dict[str, Any]:
        """
        Search for active Buy It Now listings.

        Args:
            brand: Product brand
            model: Product model
            condition: Item condition (optional)
            limit: Maximum results to return
            min_price: Minimum price filter to exclude accessories (optional)
            max_price: Maximum price filter (optional)

        Returns:
            Dictionary with search results
        """
        # Build search query
        query = f"{brand} {model}"

        # Build filter
        filters = ["buyingOptions:{FIXED_PRICE}"]  # Only Buy It Now listings

        # Add condition filter if specified
        if condition:
            # Normalize condition to eBay standard
            normalized_condition = CONDITION_MAPPINGS.get(condition.lower(), condition)
            condition_id = self.CONDITION_IDS.get(normalized_condition)

            if condition_id:
                filters.append(f"conditionIds:{{{condition_id}}}")

        # Add price range filters to exclude accessories/parts
        if min_price and max_price:
            filters.append(f"price:[{int(min_price)}..{int(max_price)}]")
        elif min_price:
            filters.append(f"price:[{int(min_price)}..]")
        elif max_price:
            filters.append(f"price:[..{int(max_price)}]")

        # Add currency
        if min_price or max_price:
            filters.append("priceCurrency:USD")

        filter_str = ",".join(filters)

        params = {
            'q': query,
            'filter': filter_str,
            'limit': min(limit, 200),  # API max is 200
            'sort': 'price'  # Sort by price
        }

        logger.info(f"Search params: {params}")

        try:
            logger.info(f"Searching active listings: {query} ({condition})")
            result = self._make_request('item_summary/search', params)
            return result

        except Exception as e:
            logger.error(f"Active listing search failed: {e}")
            return {}


def _get_minimum_price_filter(brand: str, model: str) -> float:
    """
    Determine minimum price filter to exclude accessories and parts.

    Args:
        brand: Product brand
        model: Product model

    Returns:
        Minimum price threshold
    """
    brand_lower = brand.lower()
    model_lower = model.lower()

    # Laptops and computers - min $200
    laptop_brands = ['apple', 'dell', 'hp', 'lenovo', 'asus', 'acer', 'microsoft', 'razer', 'msi']
    laptop_keywords = ['macbook', 'laptop', 'notebook', 'chromebook', 'surface', 'thinkpad']

    if brand_lower in laptop_brands or any(kw in model_lower for kw in laptop_keywords):
        return 200.0

    # Game consoles - min $100
    console_brands = ['nintendo', 'sony', 'microsoft', 'valve']
    console_keywords = ['switch', 'playstation', 'ps4', 'ps5', 'xbox', 'steam deck']

    if brand_lower in console_brands or any(kw in model_lower for kw in console_keywords):
        return 100.0

    # Tablets - min $80
    tablet_keywords = ['ipad', 'tablet', 'tab', 'kindle']
    if any(kw in model_lower for kw in tablet_keywords):
        return 80.0

    # Smartphones - min $75
    phone_keywords = ['iphone', 'galaxy', 'pixel', 'phone']
    if any(kw in model_lower for kw in phone_keywords):
        return 75.0

    # Cameras - min $100
    camera_brands = ['canon', 'nikon', 'sony', 'fujifilm', 'panasonic', 'olympus']
    camera_keywords = ['camera', 'dslr', 'mirrorless']
    if brand_lower in camera_brands or any(kw in model_lower for kw in camera_keywords):
        return 100.0

    # Default: min $50 to exclude most accessories
    return 50.0


def analyze_active_competition(brand: str, model: str, condition: str) -> Dict[str, Any]:
    """
    Analyze active eBay listings for competitive pricing.

    Args:
        brand: Product brand
        model: Product model
        condition: Item condition

    Returns:
        Dictionary with pricing statistics
    """
    api = EbayBrowseAPI()

    # Determine minimum price based on brand/product type to exclude accessories
    min_price = _get_minimum_price_filter(brand, model)

    try:
        # Search for active listings with price filter
        results = api.search_active_listings(brand, model, condition, min_price=min_price)

        item_summaries = results.get('itemSummaries', [])
        total_count = results.get('total', 0)

        if not item_summaries:
            logger.warning(f"No active listings found for {brand} {model}")
            return {
                'avg_active_price': 0.0,
                'median_active_price': 0.0,
                'active_listing_count': 0,
                'price_range_low': 0.0,
                'price_range_high': 0.0
            }

        # Extract prices
        prices = []
        for item in item_summaries:
            price_data = item.get('price', {})
            value = price_data.get('value')

            if value:
                try:
                    prices.append(float(value))
                except (ValueError, TypeError):
                    continue

        if not prices:
            logger.warning("No valid prices found in active listings")
            return {
                'avg_active_price': 0.0,
                'median_active_price': 0.0,
                'active_listing_count': total_count,
                'price_range_low': 0.0,
                'price_range_high': 0.0
            }

        # Calculate statistics
        avg_price = statistics.mean(prices)
        median_price = statistics.median(prices)
        min_price = min(prices)
        max_price = max(prices)

        logger.info(f"Found {len(prices)} active listings, avg: ${avg_price:.2f}, median: ${median_price:.2f}")

        return {
            'avg_active_price': avg_price,
            'median_active_price': median_price,
            'active_listing_count': len(prices),
            'price_range_low': min_price,
            'price_range_high': max_price
        }

    except Exception as e:
        logger.error(f"Active competition analysis failed: {e}")
        return {
            'avg_active_price': 0.0,
            'median_active_price': 0.0,
            'active_listing_count': 0,
            'price_range_low': 0.0,
            'price_range_high': 0.0
        }
