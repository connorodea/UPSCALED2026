#!/usr/bin/env python3
"""
eBay Autolister - Advanced Inventory Management & Listing Automation
Integrates with eBay Inventory API for bulk listing creation and management
"""

import json
import csv
import requests
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
import pandas as pd
from config import CONDITION_MAPPINGS, GRADE_MAPPINGS

@dataclass
class InventoryItem:
    sku: str
    title: str
    description: str
    condition: str
    category_id: str
    price: float
    quantity: int
    brand: str = ""
    mpn: str = ""
    upc: str = ""
    grade: str = ""
    weight: float = 1.0
    dimensions: Dict[str, float] = None
    images: List[str] = None
    
    def __post_init__(self):
        if self.dimensions is None:
            self.dimensions = {"length": 10.0, "width": 10.0, "height": 10.0}
        if self.images is None:
            self.images = []

class ConditionMapper:
    """Utility class for mapping conditions and grades to eBay standards"""
    
    @staticmethod
    def map_condition(condition: str, grade: str = "") -> str:
        """
        Map condition/grade to eBay condition enum
        
        Args:
            condition: The condition string from CSV
            grade: Optional grade (PSA/BGS grade, letter grade, etc.)
            
        Returns:
            Valid eBay condition enum value
        """
        # First try to map by grade if provided
        if grade:
            grade_clean = str(grade).strip().upper()
            if grade_clean in GRADE_MAPPINGS:
                return GRADE_MAPPINGS[grade_clean]
        
        # Map by condition
        condition_clean = condition.lower().strip()
        
        # Direct mapping
        if condition_clean in CONDITION_MAPPINGS:
            return CONDITION_MAPPINGS[condition_clean]
        
        # Fuzzy matching for common variations
        for key, value in CONDITION_MAPPINGS.items():
            if key in condition_clean or condition_clean in key:
                return value
        
        # Default fallback based on common terms
        if any(term in condition_clean for term in ['new', 'mint', 'sealed']):
            return 'NEW'
        elif any(term in condition_clean for term in ['excellent', 'near mint']):
            return 'USED_EXCELLENT'
        elif any(term in condition_clean for term in ['very good', 'light']):
            return 'USED_VERY_GOOD'
        elif any(term in condition_clean for term in ['good', 'normal']):
            return 'USED_GOOD'
        elif any(term in condition_clean for term in ['acceptable', 'fair', 'heavy']):
            return 'USED_ACCEPTABLE'
        elif any(term in condition_clean for term in ['parts', 'broken', 'repair']):
            return 'FOR_PARTS_OR_NOT_WORKING'
        
        # Ultimate fallback
        logging.warning(f"Could not map condition '{condition}' with grade '{grade}', defaulting to USED_GOOD")
        return 'USED_GOOD'
    
    @staticmethod
    def get_condition_description(condition: str, grade: str = "") -> str:
        """Get a human-readable description for the condition"""
        ebay_condition = ConditionMapper.map_condition(condition, grade)
        
        descriptions = {
            'NEW': 'Brand new, unopened item in original packaging',
            'LIKE_NEW': 'Opened but in like-new condition',
            'NEW_OTHER': 'New item, may be missing original packaging',
            'NEW_WITH_DEFECTS': 'New item with minor defects',
            'CERTIFIED_REFURBISHED': 'Certified refurbished by manufacturer',
            'SELLER_REFURBISHED': 'Refurbished by seller to working condition',
            'USED_EXCELLENT': 'Used item in excellent condition',
            'USED_VERY_GOOD': 'Used item in very good condition',
            'USED_GOOD': 'Used item in good condition',
            'USED_ACCEPTABLE': 'Used item in acceptable condition',
            'FOR_PARTS_OR_NOT_WORKING': 'Item for parts or not working'
        }
        
        base_description = descriptions.get(ebay_condition, 'Used item')
        
        if grade:
            return f"{base_description} (Grade: {grade})"
        
        return base_description

class EbayAPI:
    """eBay API client with OAuth authentication and rate limiting"""
    
    def __init__(self, client_id: str, client_secret: str, sandbox: bool = True, user_token: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.user_token = user_token  # Optional pre-existing user token
        self.access_token = user_token if user_token else None
        self.token_expires = time.time() + 7200 if user_token else 0  # User tokens typically valid for 2 hours

        # API endpoints
        base_url = "https://api.sandbox.ebay.com" if sandbox else "https://api.ebay.com"
        self.inventory_url = f"{base_url}/sell/inventory/v1"
        self.oauth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token" if sandbox else "https://api.ebay.com/identity/v1/oauth2/token"

        # Rate limiting
        self.last_request = 0
        self.min_interval = 0.1  # 100ms between requests

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Get OAuth access token for API requests"""
        # If using a user token, skip OAuth flow
        if self.user_token:
            self.access_token = self.user_token
            self.logger.info("Using provided user token for authentication")
            return True

        # Check if we have a valid token already
        if self.access_token and time.time() < self.token_expires:
            return True

        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {self._get_auth_header()}'
            }

            data = {
                'grant_type': 'client_credentials',
                'scope': 'https://api.ebay.com/oauth/api_scope/sell.inventory'
            }

            response = requests.post(self.oauth_url, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires = time.time() + token_data['expires_in'] - 300  # 5min buffer

            self.logger.info("Successfully authenticated with eBay API")
            return True

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            if hasattr(response, 'text'):
                self.logger.error(f"Response: {response.text}")
            return False
    
    def _get_auth_header(self) -> str:
        """Generate base64 encoded auth header"""
        import base64
        auth_string = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(auth_string.encode()).decode()
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated API request with rate limiting"""
        if not self.authenticate():
            raise Exception("Failed to authenticate")
        
        self._rate_limit()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        url = f"{self.inventory_url}/{endpoint}"
        
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=data)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        try:
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"API request failed: {e}")
            self.logger.error(f"Response: {response.text}")
            raise

class InventoryManager:
    """Manages eBay inventory items and bulk operations"""
    
    def __init__(self, api: EbayAPI):
        self.api = api
        self.logger = logging.getLogger(__name__)
    
    def create_inventory_item(self, item: InventoryItem) -> bool:
        """Create a single inventory item"""
        try:
            # Map condition using the condition mapper
            ebay_condition = ConditionMapper.map_condition(item.condition, item.grade)
            
            inventory_data = {
                "availability": {
                    "shipToLocationAvailability": {
                        "quantity": item.quantity
                    }
                },
                "condition": ebay_condition,
                "conditionDescription": ConditionMapper.get_condition_description(item.condition, item.grade),
                "product": {
                    "title": item.title,
                    "description": item.description,
                    "aspects": {},
                    "brand": item.brand,
                    "mpn": item.mpn if item.mpn else item.sku,
                    "imageUrls": item.images[:12]  # Max 12 images
                },
                "packageWeightAndSize": {
                    "dimensions": {
                        "height": item.dimensions["height"],
                        "length": item.dimensions["length"],
                        "width": item.dimensions["width"],
                        "unit": "INCH"
                    },
                    "weight": {
                        "value": item.weight,
                        "unit": "POUND"
                    }
                }
            }
            
            # Add UPC if provided
            if item.upc:
                inventory_data["product"]["upc"] = [item.upc]
            
            # Add brand to aspects if provided
            if item.brand:
                inventory_data["product"]["aspects"]["Brand"] = [item.brand]
            
            # Add grade to aspects if provided
            if item.grade:
                inventory_data["product"]["aspects"]["Grade"] = [item.grade]
            
            response = self.api._make_request('PUT', f"inventory_item/{item.sku}", inventory_data)
            self.logger.info(f"Created inventory item: {item.sku}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create inventory item {item.sku}: {e}")
            return False
    
    def bulk_create_inventory_items(self, items: List[InventoryItem], batch_size: int = 25) -> Dict:
        """Create multiple inventory items in batches"""
        results = {"successful": [], "failed": []}
        
        # Process in batches of 25 (API limit)
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_data = {"requests": []}
            
            for item in batch:
                # Map condition using the condition mapper
                ebay_condition = ConditionMapper.map_condition(item.condition, item.grade)
                
                inventory_data = {
                    "sku": item.sku,
                    "product": {
                        "title": item.title,
                        "description": item.description,
                        "brand": item.brand,
                        "mpn": item.mpn if item.mpn else item.sku,
                        "imageUrls": item.images[:12],
                        "aspects": {}
                    },
                    "condition": ebay_condition,
                    "conditionDescription": ConditionMapper.get_condition_description(item.condition, item.grade),
                    "availability": {
                        "shipToLocationAvailability": {
                            "quantity": item.quantity
                        }
                    },
                    "packageWeightAndSize": {
                        "dimensions": {
                            "height": item.dimensions["height"],
                            "length": item.dimensions["length"],
                            "width": item.dimensions["width"],
                            "unit": "INCH"
                        },
                        "weight": {
                            "value": item.weight,
                            "unit": "POUND"
                        }
                    }
                }
                
                # Add UPC if provided
                if item.upc:
                    inventory_data["product"]["upc"] = [item.upc]
                
                # Add brand to aspects if provided
                if item.brand:
                    inventory_data["product"]["aspects"]["Brand"] = [item.brand]
                
                # Add grade to aspects if provided
                if item.grade:
                    inventory_data["product"]["aspects"]["Grade"] = [item.grade]
                
                batch_data["requests"].append(inventory_data)
            
            try:
                response = self.api._make_request('POST', 'bulk_create_or_replace_inventory_item', batch_data)
                
                # Process response
                for idx, resp in enumerate(response.get('responses', [])):
                    item_sku = batch[idx].sku
                    if resp.get('statusCode') == 200:
                        results["successful"].append(item_sku)
                    else:
                        results["failed"].append({
                            "sku": item_sku,
                            "error": resp.get('errors', ['Unknown error'])
                        })
                
                self.logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} items")
                
            except Exception as e:
                self.logger.error(f"Batch creation failed: {e}")
                for item in batch:
                    results["failed"].append({"sku": item.sku, "error": str(e)})
        
        return results
    
    def get_inventory_item(self, sku: str) -> Dict:
        """Retrieve inventory item by SKU"""
        try:
            return self.api._make_request('GET', f'inventory_item/{sku}')
        except Exception as e:
            self.logger.error(f"Failed to retrieve inventory item {sku}: {e}")
            return {}

class ListingManager:
    """Manages eBay listing offers and publication"""
    
    def __init__(self, api: EbayAPI):
        self.api = api
        self.logger = logging.getLogger(__name__)
    
    def create_offer(self, sku: str, category_id: str, price: float, 
                    marketplace_id: str = "EBAY_US") -> str:
        """Create an offer for an inventory item"""
        try:
            offer_data = {
                "sku": sku,
                "marketplaceId": marketplace_id,
                "format": "FIXED_PRICE",
                "availableQuantity": 1,  # Will be pulled from inventory
                "categoryId": category_id,
                "pricingSummary": {
                    "price": {
                        "value": str(price),
                        "currency": "USD"
                    }
                },
                "listingPolicies": {
                    "fulfillmentPolicyId": "DEFAULT",  # Replace with actual policy
                    "paymentPolicyId": "DEFAULT",      # Replace with actual policy
                    "returnPolicyId": "DEFAULT"        # Replace with actual policy
                }
            }
            
            response = self.api._make_request('POST', 'offer', offer_data)
            offer_id = response.get('offerId')
            self.logger.info(f"Created offer {offer_id} for SKU {sku}")
            return offer_id
            
        except Exception as e:
            self.logger.error(f"Failed to create offer for {sku}: {e}")
            return None
    
    def publish_offer(self, offer_id: str) -> bool:
        """Publish an offer to create active listing"""
        try:
            self.api._make_request('POST', f'offer/{offer_id}/publish')
            self.logger.info(f"Published offer {offer_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to publish offer {offer_id}: {e}")
            return False

class CSVProcessor:
    """Processes CSV files for bulk inventory management"""
    
    @staticmethod
    def load_items_from_csv(file_path: str) -> List[InventoryItem]:
        """Load inventory items from CSV file"""
        items = []
        
        try:
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                # Parse dimensions if provided
                dimensions = {"length": 10.0, "width": 10.0, "height": 10.0}
                if 'dimensions' in row and pd.notna(row['dimensions']):
                    dim_parts = str(row['dimensions']).split('x')
                    if len(dim_parts) == 3:
                        dimensions = {
                            "length": float(dim_parts[0]),
                            "width": float(dim_parts[1]),
                            "height": float(dim_parts[2])
                        }
                
                # Parse image URLs
                images = []
                if 'images' in row and pd.notna(row['images']):
                    images = [url.strip() for url in str(row['images']).split(',')]
                
                item = InventoryItem(
                    sku=str(row['sku']),
                    title=str(row['title']),
                    description=str(row['description']),
                    condition=str(row.get('condition', 'NEW')),
                    category_id=str(row['category_id']),
                    price=float(row['price']),
                    quantity=int(row.get('quantity', 1)),
                    brand=str(row.get('brand', '')),
                    mpn=str(row.get('mpn', '')),
                    upc=str(row.get('upc', '')),
                    grade=str(row.get('grade', '')),
                    weight=float(row.get('weight', 1.0)),
                    dimensions=dimensions,
                    images=images
                )
                items.append(item)
                
        except Exception as e:
            logging.error(f"Error loading CSV file {file_path}: {e}")
            
        return items

class EbayAutolister:
    """Main application class for eBay automated listing"""
    
    def __init__(self, client_id: str, client_secret: str, sandbox: bool = True, user_token: str = None):
        self.api = EbayAPI(client_id, client_secret, sandbox, user_token)
        self.inventory = InventoryManager(self.api)
        self.listings = ListingManager(self.api)
        self.logger = logging.getLogger(__name__)
        
    def process_csv_file(self, csv_path: str, create_listings: bool = False) -> Dict:
        """Process CSV file and create inventory items and optionally listings"""
        items = CSVProcessor.load_items_from_csv(csv_path)
        
        if not items:
            self.logger.error("No items found in CSV file")
            return {"success": False, "message": "No items found"}
        
        # Create inventory items
        self.logger.info(f"Creating {len(items)} inventory items...")
        inventory_results = self.inventory.bulk_create_inventory_items(items)
        
        results = {
            "inventory_created": len(inventory_results["successful"]),
            "inventory_failed": len(inventory_results["failed"]),
            "failed_items": inventory_results["failed"]
        }
        
        if create_listings:
            # Create and publish listings for successful inventory items
            listings_created = 0
            listings_failed = 0
            
            for item in items:
                if item.sku in inventory_results["successful"]:
                    offer_id = self.listings.create_offer(
                        item.sku, item.category_id, item.price
                    )
                    
                    if offer_id:
                        if self.listings.publish_offer(offer_id):
                            listings_created += 1
                        else:
                            listings_failed += 1
                    else:
                        listings_failed += 1
            
            results.update({
                "listings_created": listings_created,
                "listings_failed": listings_failed
            })
        
        return results
    
    def create_sample_csv(self, file_path: str = "sample_products.csv"):
        """Create a sample CSV file for testing with your specific condition inputs"""
        sample_data = [
            {
                "sku": "LIKE-NEW-001",
                "title": "iPad Air 5th Gen - Like New Condition",
                "description": "iPad Air 5th generation in like new condition, minimal signs of use",
                "condition": "like new",
                "grade": "",
                "upc": "194252521175",
                "category_id": "171485",  # Tablets & eBook Readers
                "price": 449.99,
                "quantity": 1,
                "brand": "Apple",
                "mpn": "MM9F3LL/A",
                "weight": 1.0,
                "dimensions": "10x7x0.3",
                "images": "https://example.com/ipad1.jpg,https://example.com/ipad2.jpg"
            },
            {
                "sku": "VERY-GOOD-002",
                "title": "MacBook Pro 13-inch - Very Good Condition",
                "description": "MacBook Pro 13-inch in very good condition, light wear on corners",
                "condition": "very good",
                "grade": "",
                "upc": "194252056844",
                "category_id": "111422",  # Apple Laptops
                "price": 899.99,
                "quantity": 1,
                "brand": "Apple",
                "mpn": "MYD82LL/A",
                "weight": 3.0,
                "dimensions": "12x8x1",
                "images": "https://example.com/macbook1.jpg"
            },
            {
                "sku": "GOOD-003",
                "title": "Nintendo Switch Console - Good Condition",
                "description": "Nintendo Switch console in good condition, works perfectly with normal wear",
                "condition": "good",
                "grade": "",
                "upc": "045496452063",
                "category_id": "139971",  # Video Game Consoles
                "price": 199.99,
                "quantity": 2,
                "brand": "Nintendo",
                "mpn": "HAC-001(-01)",
                "weight": 1.5,
                "dimensions": "9x4x1",
                "images": "https://example.com/switch1.jpg,https://example.com/switch2.jpg"
            },
            {
                "sku": "ACCEPTABLE-004",
                "title": "iPhone 12 - Acceptable Condition",
                "description": "iPhone 12 in acceptable condition, heavy wear but fully functional",
                "condition": "acceptable",
                "grade": "",
                "upc": "194252031407",
                "category_id": "9355",  # Cell Phones & Smartphones
                "price": 299.99,
                "quantity": 1,
                "brand": "Apple",
                "mpn": "MGJ53LL/A",
                "weight": 0.8,
                "dimensions": "6x3x0.3",
                "images": "https://example.com/iphone12.jpg"
            },
            {
                "sku": "SALVAGE-005",
                "title": "Samsung Galaxy S21 - Salvage/Parts Only",
                "description": "Samsung Galaxy S21 for parts or repair, cracked screen, battery issues",
                "condition": "salvage",
                "grade": "",
                "upc": "887276459042",
                "category_id": "9355",  # Cell Phones & Smartphones
                "price": 89.99,
                "quantity": 1,
                "brand": "Samsung",
                "mpn": "SM-G991U",
                "weight": 0.7,
                "dimensions": "6x3x0.3",
                "images": "https://example.com/galaxy_salvage.jpg"
            }
        ]
        
        df = pd.DataFrame(sample_data)
        df.to_csv(file_path, index=False)
        self.logger.info(f"Sample CSV created: {file_path}")

def main():
    """Example usage"""
    # Initialize with your eBay API credentials
    client_id = os.getenv('EBAY_CLIENT_ID')
    client_secret = os.getenv('EBAY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Please set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET environment variables")
        return
    
    # Create autolister instance
    autolister = EbayAutolister(client_id, client_secret, sandbox=True)
    
    # Create sample CSV for testing
    autolister.create_sample_csv()
    
    # Process CSV file (inventory only, no listings)
    results = autolister.process_csv_file("sample_products.csv", create_listings=False)
    
    print("Processing Results:")
    print(f"Inventory items created: {results['inventory_created']}")
    print(f"Inventory items failed: {results['inventory_failed']}")
    
    if results['failed_items']:
        print("Failed items:")
        for failed in results['failed_items']:
            print(f"  SKU: {failed['sku']}, Error: {failed['error']}")

if __name__ == "__main__":
    main()