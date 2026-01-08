#!/usr/bin/env python3
"""
Configuration management for eBay Autolister
"""

import os
from dotenv import load_dotenv
from typing import Dict, Optional
import json

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration manager for eBay Autolister"""
    
    def __init__(self):
        self.ebay_sandbox = os.getenv('EBAY_SANDBOX', 'true').lower() == 'true'
        self.ebay_client_id = os.getenv('EBAY_CLIENT_ID', '')
        self.ebay_client_secret = os.getenv('EBAY_CLIENT_SECRET', '')
        
        # API Configuration
        self.rate_limit_interval = float(os.getenv('RATE_LIMIT_INTERVAL', '0.1'))
        self.batch_size = int(os.getenv('BATCH_SIZE', '25'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'ebay_autolister.log')
        
        # Default business policies (replace with your actual policy IDs)
        self.default_fulfillment_policy = os.getenv('DEFAULT_FULFILLMENT_POLICY', '')
        self.default_payment_policy = os.getenv('DEFAULT_PAYMENT_POLICY', '')
        self.default_return_policy = os.getenv('DEFAULT_RETURN_POLICY', '')
        
        # Marketplace settings
        self.default_marketplace = os.getenv('DEFAULT_MARKETPLACE', 'EBAY_US')
        self.default_currency = os.getenv('DEFAULT_CURRENCY', 'USD')
        
        # Image settings
        self.max_images_per_listing = int(os.getenv('MAX_IMAGES_PER_LISTING', '12'))
        self.image_resize_enabled = os.getenv('IMAGE_RESIZE_ENABLED', 'true').lower() == 'true'
        self.max_image_size_mb = float(os.getenv('MAX_IMAGE_SIZE_MB', '10.0'))
    
    def validate(self) -> bool:
        """Validate that required configuration is present"""
        required_fields = [
            'ebay_client_id',
            'ebay_client_secret'
        ]
        
        missing_fields = [field for field in required_fields if not getattr(self, field)]
        
        if missing_fields:
            print(f"Missing required configuration: {', '.join(missing_fields)}")
            return False
            
        return True
    
    def get_api_base_url(self) -> str:
        """Get the appropriate API base URL"""
        if self.ebay_sandbox:
            return "https://api.sandbox.ebay.com"
        else:
            return "https://api.ebay.com"
    
    def get_oauth_url(self) -> str:
        """Get the OAuth endpoint URL"""
        if self.ebay_sandbox:
            return "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
        else:
            return "https://api.ebay.com/identity/v1/oauth2/token"
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary (excluding secrets)"""
        return {
            'ebay_sandbox': self.ebay_sandbox,
            'rate_limit_interval': self.rate_limit_interval,
            'batch_size': self.batch_size,
            'max_retries': self.max_retries,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'default_marketplace': self.default_marketplace,
            'default_currency': self.default_currency,
            'max_images_per_listing': self.max_images_per_listing,
            'image_resize_enabled': self.image_resize_enabled,
            'max_image_size_mb': self.max_image_size_mb
        }

# Category mappings for common product types
CATEGORY_MAPPINGS = {
    'electronics': '58058',      # Cell Phones & Accessories
    'clothing': '11450',         # Clothing, Shoes & Accessories
    'home_garden': '11700',      # Home & Garden
    'automotive': '6000',        # eBay Motors
    'collectibles': '1',         # Collectibles
    'books': '267',              # Books
    'toys': '220',               # Toys & Hobbies
    'jewelry': '281',            # Jewelry & Watches
    'sports': '888',             # Sporting Goods
    'health_beauty': '26395'     # Health & Beauty
}

# Comprehensive condition mappings for eBay
CONDITION_MAPPINGS = {
    # Primary condition inputs (your system's conditions)
    'like new': 'LIKE_NEW',           # 1) Like New
    'very good': 'USED_VERY_GOOD',   # 2) Very Good  
    'good': 'USED_GOOD',             # 3) Good
    'acceptable': 'USED_ACCEPTABLE', # 4) Acceptable
    'salvage': 'FOR_PARTS_OR_NOT_WORKING',  # 5) Salvage
    
    # Alternative spellings and variations
    'likenew': 'LIKE_NEW',
    'like-new': 'LIKE_NEW',
    'verygood': 'USED_VERY_GOOD',
    'very-good': 'USED_VERY_GOOD',
    'vgood': 'USED_VERY_GOOD',
    'v good': 'USED_VERY_GOOD',
    'vg': 'USED_VERY_GOOD',
    
    # Standard conditions
    'new': 'NEW',
    'brand new': 'NEW',
    'sealed': 'NEW',
    'mint': 'NEW',
    'unopened': 'NEW',
    
    # Open box / Other new conditions
    'open box': 'NEW_OTHER',
    'new open box': 'NEW_OTHER',
    'new other': 'NEW_OTHER',
    'new without tags': 'NEW_OTHER',
    'graded': 'LIKE_NEW',  # For trading cards
    
    # New with issues
    'new with defects': 'NEW_WITH_DEFECTS',
    'new damaged': 'NEW_WITH_DEFECTS',
    'new imperfect': 'NEW_WITH_DEFECTS',
    
    # Refurbished conditions
    'certified refurbished': 'CERTIFIED_REFURBISHED',
    'manufacturer refurbished': 'CERTIFIED_REFURBISHED',
    'excellent refurbished': 'EXCELLENT_REFURBISHED',
    'very good refurbished': 'VERY_GOOD_REFURBISHED',
    'good refurbished': 'GOOD_REFURBISHED',
    'seller refurbished': 'SELLER_REFURBISHED',
    'refurbished': 'SELLER_REFURBISHED',
    'renewed': 'SELLER_REFURBISHED',
    'restored': 'SELLER_REFURBISHED',
    
    # Extended used conditions
    'used excellent': 'USED_EXCELLENT',
    'used like new': 'LIKE_NEW',
    'excellent': 'USED_EXCELLENT',
    'near mint': 'LIKE_NEW',
    
    'used very good': 'USED_VERY_GOOD',
    'light wear': 'USED_VERY_GOOD',
    
    'used good': 'USED_GOOD',
    'moderate wear': 'USED_GOOD',
    'normal wear': 'USED_GOOD',
    
    'used acceptable': 'USED_ACCEPTABLE',
    'fair': 'USED_ACCEPTABLE',
    'heavy wear': 'USED_ACCEPTABLE',
    'well used': 'USED_ACCEPTABLE',
    
    # Apparel specific
    'pre owned excellent': 'PRE_OWNED_EXCELLENT',
    'pre owned fair': 'PRE_OWNED_FAIR',
    'pre-owned excellent': 'PRE_OWNED_EXCELLENT',
    'pre-owned fair': 'PRE_OWNED_FAIR',
    
    # Parts/repair/salvage
    'for parts': 'FOR_PARTS_OR_NOT_WORKING',
    'not working': 'FOR_PARTS_OR_NOT_WORKING',
    'broken': 'FOR_PARTS_OR_NOT_WORKING',
    'parts only': 'FOR_PARTS_OR_NOT_WORKING',
    'repair': 'FOR_PARTS_OR_NOT_WORKING',
    'damaged': 'FOR_PARTS_OR_NOT_WORKING',
    'scrap': 'FOR_PARTS_OR_NOT_WORKING',
    'parts': 'FOR_PARTS_OR_NOT_WORKING'
}

# Grade mappings (common grading systems)
GRADE_MAPPINGS = {
    # PSA/BGS grading (1-10 scale)
    '10': 'LIKE_NEW',  # Gem Mint
    '9.5': 'LIKE_NEW', # Mint+
    '9': 'LIKE_NEW',   # Mint
    '8.5': 'USED_EXCELLENT', # Near Mint+
    '8': 'USED_EXCELLENT',   # Near Mint
    '7.5': 'USED_VERY_GOOD', # Excellent+
    '7': 'USED_VERY_GOOD',   # Excellent
    '6.5': 'USED_GOOD',      # Excellent-
    '6': 'USED_GOOD',        # Very Good
    '5': 'USED_ACCEPTABLE',  # Good
    '4': 'USED_ACCEPTABLE',  # Very Good-
    '3': 'USED_ACCEPTABLE',  # Good-
    '2': 'FOR_PARTS_OR_NOT_WORKING', # Fair
    '1': 'FOR_PARTS_OR_NOT_WORKING', # Poor
    
    # Letter grades
    'A+': 'LIKE_NEW',
    'A': 'USED_EXCELLENT',
    'A-': 'USED_EXCELLENT',
    'B+': 'USED_VERY_GOOD',
    'B': 'USED_VERY_GOOD',
    'B-': 'USED_GOOD',
    'C+': 'USED_GOOD',
    'C': 'USED_ACCEPTABLE',
    'C-': 'USED_ACCEPTABLE',
    'D': 'FOR_PARTS_OR_NOT_WORKING',
    'F': 'FOR_PARTS_OR_NOT_WORKING'
}

# Pricing Configuration
PRICING_CONFIG = {
    'base_multiplier': 0.92,  # 92% of average sold price
    'condition_penalties': {
        'LIKE_NEW': 0.00,           # -0%
        'USED_EXCELLENT': 0.05,      # -5%
        'USED_VERY_GOOD': 0.10,      # -10%
        'USED_GOOD': 0.10,           # -10%
        'USED_ACCEPTABLE': 0.20,     # -20%
        'FOR_PARTS_OR_NOT_WORKING': 0.50  # -50%
    },
    'cache_duration_hours': 24,
    'sold_items_lookback_days': 30,
    'min_sold_samples': 3,  # Minimum sold items to calculate reliable avg
    'outlier_threshold': 2.5,  # Standard deviations for outlier removal
    'fallback_msrp_multiplier': 0.50  # Use 50% MSRP when no market data
}

# Best Offer Configuration
BEST_OFFER_CONFIG = {
    'enabled': True,
    'min_offer_percentage': 0.85,  # 85% of BIN price
    'auto_accept_percentage': 0.95,  # Auto-accept at 95% of BIN
    'auto_decline_percentage': 0.75,  # Auto-decline below 75% of BIN
}

# Auction Configuration (if using auction format)
AUCTION_CONFIG = {
    'starting_price_percentage': 0.70,  # 70% of calculated price
    'reserve_price_percentage': 0.90,   # 90% of calculated price
}

def create_sample_env():
    """Create a sample .env file with required variables"""
    env_content = """# eBay API Configuration
EBAY_CLIENT_ID=your_client_id_here
EBAY_CLIENT_SECRET=your_client_secret_here
EBAY_SANDBOX=true

# API Settings
RATE_LIMIT_INTERVAL=0.1
BATCH_SIZE=25
MAX_RETRIES=3

# Logging
LOG_LEVEL=INFO
LOG_FILE=ebay_autolister.log

# Business Policies (replace with your actual policy IDs)
DEFAULT_FULFILLMENT_POLICY=your_fulfillment_policy_id
DEFAULT_PAYMENT_POLICY=your_payment_policy_id
DEFAULT_RETURN_POLICY=your_return_policy_id

# Marketplace Settings
DEFAULT_MARKETPLACE=EBAY_US
DEFAULT_CURRENCY=USD

# Image Settings
MAX_IMAGES_PER_LISTING=12
IMAGE_RESIZE_ENABLED=true
MAX_IMAGE_SIZE_MB=10.0
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("Sample .env file created. Please update with your actual credentials.")
    else:
        print(".env file already exists.")

if __name__ == "__main__":
    # Create sample .env file
    create_sample_env()
    
    # Test configuration
    config = Config()
    print("Configuration loaded:")
    print(json.dumps(config.to_dict(), indent=2))
    
    if config.validate():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration validation failed")