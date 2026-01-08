# eBay Autolister Testing Setup Guide

## 🔑 Step 1: Get eBay API Credentials

### 1.1 Create eBay Developer Account
1. Go to [eBay Developers](https://developer.ebay.com)
2. Sign in or create an account
3. Navigate to "My Account" → "Keys"

### 1.2 Create Application Keys
1. Click "Create Application Keys"
2. Choose "Production" or "Sandbox" environment
3. Application Type: "Public Application"
4. Grant Type: "Client Credentials Grant"
5. Scopes needed:
   - `https://api.ebay.com/oauth/api_scope/sell.inventory`
   - `https://api.ebay.com/oauth/api_scope/sell.inventory.readonly`

### 1.3 Get Your Credentials
You'll receive:
- **App ID (Client ID)**: Your application identifier
- **Cert ID (Client Secret)**: Your application secret

## ⚙️ Step 2: Configure Environment

### 2.1 Update .env File
Replace the placeholders in `.env`:
```bash
# eBay API Configuration
EBAY_CLIENT_ID=YourActualClientID_Here
EBAY_CLIENT_SECRET=YourActualClientSecret_Here
EBAY_SANDBOX=true  # Set to false for production

# Business Policies - Get these from eBay seller account
DEFAULT_FULFILLMENT_POLICY=your_actual_fulfillment_policy_id
DEFAULT_PAYMENT_POLICY=your_actual_payment_policy_id
DEFAULT_RETURN_POLICY=your_actual_return_policy_id
```

### 2.2 Get Business Policy IDs
1. Log into your eBay seller account
2. Go to "Account" → "Site Preferences" → "Business Policies"
3. Create or find your:
   - **Payment Policy** (e.g., PayPal, credit cards)
   - **Return Policy** (e.g., 30-day returns)
   - **Shipping Policy** (e.g., standard shipping)
4. Copy the Policy IDs and update your `.env` file

## 🧪 Step 3: Test Authentication

Run the connection test:
```bash
python cli.py test-connection
```

Expected output:
```
✅ Authentication successful
🌐 Connected to: https://api.sandbox.ebay.com
📍 Marketplace: EBAY_US
```

## 📝 Step 4: Test Inventory Creation

### 4.1 Dry Run Test
```bash
python cli.py process your_conditions.csv --dry-run
```

### 4.2 Create Inventory Items (No Listings)
```bash
python cli.py process your_conditions.csv
```

### 4.3 Check Inventory Item
```bash
python cli.py check LIKE-NEW-001
```

## 🛍️ Step 5: Test Full Listing Creation

### 5.1 Create Inventory + Listings
```bash
python cli.py process your_conditions.csv --create-listings
```

### 5.2 Monitor Results
Check the output for:
- ✅ Inventory items created
- ✅ Listings created
- ❌ Any failures and error messages

## 🔍 Step 6: Verify on eBay

### Sandbox Environment
1. Go to [eBay Sandbox](https://sandbox.ebay.com)
2. Log in with your sandbox seller account
3. Navigate to "My eBay" → "Selling" → "Active Listings"
4. Verify your test listings appear

### Production Environment
1. Go to [eBay.com](https://www.ebay.com)
2. Log in to your seller account
3. Check "My eBay" → "Selling" → "Active Listings"

## 🚨 Common Issues & Solutions

### Authentication Failed
- ✅ Verify Client ID and Secret are correct
- ✅ Check if scopes are properly configured
- ✅ Ensure sandbox/production setting matches your keys

### Business Policy Errors
- ✅ Create payment, shipping, and return policies in eBay seller account
- ✅ Copy exact Policy IDs to `.env` file
- ✅ Ensure policies are active and published

### Category ID Issues
- ✅ Use eBay's Category API to find valid category IDs
- ✅ Check category hierarchy requirements
- ✅ Some categories require additional item specifics

### Rate Limiting
- ✅ Increase `RATE_LIMIT_INTERVAL` in `.env`
- ✅ Check eBay API usage limits in developer console
- ✅ Use sandbox environment for testing

### Item Specifics Required
Some categories require specific item details:
- ✅ Brand (usually required)
- ✅ Model/MPN (often required)
- ✅ UPC (recommended)
- ✅ Condition (always required)

## 🎯 Testing Checklist

- [ ] eBay developer account created
- [ ] Application keys obtained
- [ ] Business policies configured
- [ ] `.env` file updated with real credentials
- [ ] Authentication test passes
- [ ] Inventory creation test passes
- [ ] Individual item check works
- [ ] Full listing creation test passes
- [ ] Listings visible on eBay (sandbox/production)

## 📞 Getting Help

If you encounter issues:

1. **Check Logs**: Review `ebay_autolister.log` for detailed error messages
2. **Verbose Mode**: Use `-v` flag for more detailed output
3. **eBay Developer Support**: [developer.ebay.com/support](https://developer.ebay.com/support)
4. **API Documentation**: [eBay Inventory API](https://developer.ebay.com/api-docs/sell/inventory/overview.html)

## ⚡ Quick Test Commands

```bash
# Test everything step by step
python cli.py config-info                    # Check configuration
python cli.py test-connection                # Test authentication
python cli.py create-sample test.csv         # Create test data
python cli.py process test.csv --dry-run     # Preview actions
python cli.py process test.csv               # Create inventory
python cli.py check TEST-001                 # Verify creation
python cli.py process test.csv --create-listings  # Create listings
```