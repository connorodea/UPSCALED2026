#!/usr/bin/env python3
"""
Test eBay API connection and verify credentials.
"""

import os
from dotenv import load_dotenv
from ebay_autolister import EbayAPI

# Load environment variables
load_dotenv()

def test_connection():
    """Test eBay API connection"""
    print("\n" + "=" * 80)
    print("EBAY API CONNECTION TEST")
    print("=" * 80)

    # Load credentials
    client_id = os.getenv('EBAY_CLIENT_ID')
    client_secret = os.getenv('EBAY_CLIENT_SECRET')
    user_token = os.getenv('EBAY_AUTH_TOKEN')
    sandbox = os.getenv('EBAY_SANDBOX', 'true').lower() == 'true'

    # Display configuration
    print("\nConfiguration:")
    print(f"  Client ID: {client_id[:20]}..." if client_id else "  Client ID: NOT SET")
    print(f"  Client Secret: {client_secret[:20]}..." if client_secret else "  Client Secret: NOT SET")
    print(f"  User Token: {user_token[:30]}..." if user_token else "  User Token: NOT SET")
    print(f"  Environment: {'SANDBOX (Testing)' if sandbox else 'PRODUCTION (Live eBay)'}")

    if not client_id or not client_secret:
        print("\n✗ ERROR: Missing eBay credentials in .env file")
        return False

    # Test authentication
    print("\n" + "-" * 80)
    print("Testing authentication...")
    print("-" * 80)

    try:
        api = EbayAPI(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=sandbox,
            user_token=user_token
        )

        if api.authenticate():
            print("\n✓ SUCCESS: Authentication successful!")
            print(f"  Access token obtained: {api.access_token[:30]}...")
            print(f"  Token expires in: {int(api.token_expires - __import__('time').time())} seconds")

            if not sandbox:
                print("\n⚠️  WARNING: You are connected to PRODUCTION eBay!")
                print("  Any listings created will be LIVE on eBay.com")
                print("  Make sure this is intentional.")
            else:
                print("\n✓ You are connected to SANDBOX eBay")
                print("  This is a safe testing environment")

            return True
        else:
            print("\n✗ FAILED: Authentication failed")
            print("  Check your credentials and try again")
            return False

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False

    finally:
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
