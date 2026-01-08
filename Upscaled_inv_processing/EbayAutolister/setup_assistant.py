#!/usr/bin/env python3
"""
eBay Autolister Setup Assistant
Interactive setup to configure eBay API credentials
"""

import os
import re
from pathlib import Path

def print_header():
    print("🚀 eBay Autolister Setup Assistant")
    print("=" * 50)
    print()

def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default"""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    else:
        response = input(f"{prompt}: ").strip()
        return response

def validate_client_id(client_id: str) -> bool:
    """Basic validation for eBay client ID"""
    # eBay client IDs are typically 32 character alphanumeric strings
    return len(client_id) > 20 and client_id.replace('-', '').isalnum()

def validate_client_secret(client_secret: str) -> bool:
    """Basic validation for eBay client secret"""
    # eBay client secrets are typically longer alphanumeric strings
    return len(client_secret) > 30 and client_secret.replace('-', '').isalnum()

def create_env_file(config: dict):
    """Create or update .env file with user configuration"""
    env_content = f"""# eBay API Configuration
EBAY_CLIENT_ID={config['client_id']}
EBAY_CLIENT_SECRET={config['client_secret']}
EBAY_SANDBOX={config['sandbox']}

# API Settings
RATE_LIMIT_INTERVAL=0.1
BATCH_SIZE=25
MAX_RETRIES=3

# Logging
LOG_LEVEL=INFO
LOG_FILE=ebay_autolister.log

# Business Policies (replace with your actual policy IDs)
DEFAULT_FULFILLMENT_POLICY={config['fulfillment_policy']}
DEFAULT_PAYMENT_POLICY={config['payment_policy']}
DEFAULT_RETURN_POLICY={config['return_policy']}

# Marketplace Settings
DEFAULT_MARKETPLACE=EBAY_US
DEFAULT_CURRENCY=USD

# Image Settings
MAX_IMAGES_PER_LISTING=12
IMAGE_RESIZE_ENABLED=true
MAX_IMAGE_SIZE_MB=10.0
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file updated successfully!")

def main():
    print_header()
    
    print("This assistant will help you configure your eBay API credentials.")
    print("You'll need to have:")
    print("1. eBay Developer Account (https://developer.ebay.com)")
    print("2. Application Keys (Client ID and Client Secret)")
    print("3. Business Policies set up in your eBay seller account")
    print()
    
    # Step 1: Get eBay API Credentials
    print("📋 Step 1: eBay API Credentials")
    print("-" * 30)
    
    # Check if user has credentials
    has_credentials = get_user_input("Do you have eBay API credentials? (y/n)", "n").lower().startswith('y')
    
    if not has_credentials:
        print()
        print("🔗 To get eBay API credentials:")
        print("1. Go to https://developer.ebay.com")
        print("2. Sign in or create an account")
        print("3. Go to 'My Account' → 'Keys'")
        print("4. Click 'Create Application Keys'")
        print("5. Choose 'Sandbox' for testing or 'Production' for live")
        print("6. Application Type: 'Public Application'")
        print("7. Grant Type: 'Client Credentials Grant'")
        print("8. Scopes: 'sell.inventory' and 'sell.inventory.readonly'")
        print()
        
        input("Press Enter when you have obtained your credentials...")
        print()
    
    # Get credentials
    client_id = get_user_input("Enter your eBay Client ID (App ID)")
    while not validate_client_id(client_id):
        print("❌ Invalid Client ID format. Please check and try again.")
        client_id = get_user_input("Enter your eBay Client ID (App ID)")
    
    client_secret = get_user_input("Enter your eBay Client Secret (Cert ID)")
    while not validate_client_secret(client_secret):
        print("❌ Invalid Client Secret format. Please check and try again.")
        client_secret = get_user_input("Enter your eBay Client Secret (Cert ID)")
    
    # Step 2: Environment Selection
    print()
    print("📋 Step 2: Environment Selection")
    print("-" * 30)
    
    sandbox = get_user_input("Use Sandbox environment for testing? (y/n)", "y").lower().startswith('y')
    sandbox_str = "true" if sandbox else "false"
    
    if sandbox:
        print("✅ Using Sandbox - safe for testing, no real listings created")
    else:
        print("⚠️  Using Production - will create real eBay listings!")
        confirm = get_user_input("Are you sure you want to use Production? (y/n)", "n")
        if not confirm.lower().startswith('y'):
            sandbox = True
            sandbox_str = "true"
            print("✅ Switched to Sandbox for safety")
    
    # Step 3: Business Policies
    print()
    print("📋 Step 3: Business Policies")
    print("-" * 30)
    
    has_policies = get_user_input("Do you have eBay business policies set up? (y/n)", "n").lower().startswith('y')
    
    if not has_policies:
        print()
        print("🔗 To set up eBay business policies:")
        print("1. Log into your eBay seller account")
        print("2. Go to 'Account' → 'Site Preferences' → 'Business Policies'")
        print("3. Create policies for:")
        print("   • Payment (e.g., PayPal, credit cards)")
        print("   • Shipping/Fulfillment (e.g., standard shipping)")
        print("   • Returns (e.g., 30-day returns)")
        print("4. Copy the Policy IDs from each policy")
        print()
        
        input("Press Enter when you have created your business policies...")
        print()
    
    payment_policy = get_user_input("Enter Payment Policy ID", "your_payment_policy_id")
    fulfillment_policy = get_user_input("Enter Fulfillment/Shipping Policy ID", "your_fulfillment_policy_id")
    return_policy = get_user_input("Enter Return Policy ID", "your_return_policy_id")
    
    # Step 4: Summary and Confirmation
    print()
    print("📋 Step 4: Configuration Summary")
    print("-" * 30)
    print(f"Client ID: {client_id[:8]}...")
    print(f"Client Secret: {client_secret[:8]}...")
    print(f"Environment: {'Sandbox' if sandbox else 'Production'}")
    print(f"Payment Policy: {payment_policy}")
    print(f"Fulfillment Policy: {fulfillment_policy}")
    print(f"Return Policy: {return_policy}")
    print()
    
    confirm = get_user_input("Save this configuration? (y/n)", "y")
    
    if confirm.lower().startswith('y'):
        config = {
            'client_id': client_id,
            'client_secret': client_secret,
            'sandbox': sandbox_str,
            'payment_policy': payment_policy,
            'fulfillment_policy': fulfillment_policy,
            'return_policy': return_policy
        }
        
        create_env_file(config)
        
        print()
        print("🎉 Setup Complete!")
        print()
        print("Next steps:")
        print("1. Test your configuration:")
        print("   python cli.py test-connection")
        print()
        print("2. Run the test suite:")
        print("   python test_suite.py")
        print()
        print("3. Create your first listings:")
        print("   python cli.py process your_conditions.csv --dry-run")
        print("   python cli.py process your_conditions.csv")
        
    else:
        print("❌ Configuration not saved. Run this script again when ready.")

if __name__ == "__main__":
    main()