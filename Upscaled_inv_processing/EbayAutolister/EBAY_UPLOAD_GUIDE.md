# eBay Upload Guide - AI Agent Workflow

Complete guide for uploading your enriched products to eBay with confirmation.

## Quick Start

### Step 1: Prepare Your CSV

Your CSV file should have these columns:
- `sku` - Unique product SKU
- `brand` - Product brand/manufacturer
- `model` - Product model name/number
- `condition` - Item condition (like new, very good, good, acceptable, salvage)

Example CSV (`B1.csv`):
```csv
sku,brand,model,condition
ITEM-001,Apple,iPad Air 5th Gen,like new
ITEM-002,Nintendo,Switch OLED,very good
ITEM-003,Samsung,Galaxy S23,good
```

### Step 2: Set Up eBay Credentials

Add your eBay API credentials to `.env`:

```bash
# OpenAI Configuration (already set)
OPENAI_API_KEY=sk-proj-...

# eBay API Configuration (add these)
EBAY_CLIENT_ID=your_ebay_app_client_id
EBAY_CLIENT_SECRET=your_ebay_app_client_secret
EBAY_SANDBOX=true  # Use 'false' for production

# eBay Business Policies (optional, for production)
DEFAULT_FULFILLMENT_POLICY=your_policy_id
DEFAULT_PAYMENT_POLICY=your_policy_id
DEFAULT_RETURN_POLICY=your_policy_id
```

**Getting eBay Credentials:**
1. Go to https://developer.ebay.com/
2. Create a developer account
3. Create an application
4. Get your Client ID and Client Secret

### Step 3: Run the Workflow

#### Option A: Interactive Mode (Recommended)

```bash
cd EbayAutolister
python run_workflow.py
```

Or with a specific file:
```bash
python run_workflow.py your_products.csv
```

You'll see an interactive menu:
```
What would you like to do?
  1. Enrich products only (no eBay upload)
  2. Enrich + Create inventory items (no listings)
  3. Enrich + Create inventory + Publish listings to eBay

Enter your choice (1-3): 3

⚠️  WARNING: This will publish listings to eBay!
✓ You are using SANDBOX mode (safe for testing)

Are you sure you want to proceed? (yes/no): yes
```

#### Option B: Direct Python Script

```bash
python integrated_workflow.py B1.csv
```

## Workflow Stages

### Stage 1: AI Enrichment ⚙️
The AI agents will:
- Research each product online
- Find retail/MSRP prices
- Determine best eBay category
- Generate SEO-optimized titles
- Create detailed descriptions
- Extract item specifics
- Estimate shipping details

**Pricing: All items will be priced at 50% of MSRP**

### Stage 2: Inventory Creation 📦
Creates inventory items in eBay with:
- Product details
- Pricing (50% of MSRP)
- Images
- Shipping info
- Condition details

### Stage 3: Listing Publication 🏪
(Only if you selected option 3)
- Creates offers for each inventory item
- Publishes listings to eBay
- Makes items live and searchable

## Understanding the Output

### Summary Report

After the workflow completes, you'll see:

```
================================================================================
EBAY LISTING WORKFLOW - SUMMARY REPORT
================================================================================

📊 ENRICHMENT RESULTS
--------------------------------------------------------------------------------
Products Processed:       10
Enriched CSV Saved:       enriched_20250126_143022.csv

📦 INVENTORY CREATION RESULTS
--------------------------------------------------------------------------------
✓ Successfully Created:   10
✗ Failed:                 0

🏪 EBAY LISTING PUBLICATION RESULTS
--------------------------------------------------------------------------------
✓ Successfully Published: 10
✗ Failed:                 0

✓ SUCCESSFULLY PUBLISHED LISTINGS:
  • ITEM-001: Apple iPad Air 5th Gen - Like New
    Price: $299.50 | Offer ID: 1234567890

  • ITEM-002: Nintendo Switch OLED - Very Good Condition
    Price: $174.50 | Offer ID: 1234567891

================================================================================
OVERALL SUCCESS RATE: 100.0% (10/10)
================================================================================

💾 Results saved to: workflow_results_20250126_143022.json
```

### Output Files

The workflow creates several files:

1. **Enriched CSV** (`enriched_YYYYMMDD_HHMMSS.csv`)
   - All your products with enriched data
   - Includes titles, descriptions, pricing, categories, etc.

2. **Results JSON** (`workflow_results_YYYYMMDD_HHMMSS.json`)
   - Detailed results of the workflow
   - Success/failure counts
   - List of published listings with offer IDs

3. **Log File** (`integrated_workflow.log`)
   - Detailed execution log
   - Useful for debugging

## Confirmation Before Publishing

The workflow includes safety features:

### 1. Interactive Confirmation
When you select option 3 (publish to eBay), you'll be asked to confirm:
```
⚠️  WARNING: This will publish listings to eBay!
✓ You are using SANDBOX mode (safe for testing)

Are you sure you want to proceed? (yes/no):
```

### 2. Sandbox vs Production
- **Sandbox mode** (`EBAY_SANDBOX=true`)
  - Safe for testing
  - Listings won't appear on real eBay
  - Use this to test your workflow

- **Production mode** (`EBAY_SANDBOX=false`)
  - Real listings will be created
  - Items will be visible on eBay.com
  - Only use after testing in sandbox

### 3. Detailed Reporting
After publishing, you get:
- List of successfully published items with SKU and Offer ID
- List of failed items with error messages
- Overall success rate
- Links to view your listings (in production)

## Troubleshooting

### "Missing EBAY_CLIENT_ID"
**Problem:** eBay credentials not configured

**Solution:** Add your eBay API credentials to `.env` file

### "Authentication failed"
**Problem:** Invalid eBay credentials

**Solution:**
- Verify your Client ID and Client Secret
- Check if you're using sandbox credentials with `EBAY_SANDBOX=true`
- Ensure credentials are for the correct environment

### "Failed to create offer"
**Problem:** Missing business policies

**Solution:**
- Create business policies in eBay Seller Hub
- Add policy IDs to `.env` file
- Or update `ebay_autolister.py` to use policy names instead of IDs

### "Category not found"
**Problem:** Invalid eBay category ID

**Solution:**
- The AI will try to determine the correct category
- If it fails, it defaults to category "58058" (General)
- You can manually specify categories in your CSV

### Listings not appearing
**Problem:** Using sandbox mode

**Solution:**
- Sandbox listings only appear in the sandbox environment
- To see real listings, set `EBAY_SANDBOX=false` and use production credentials

## Best Practices

### 1. Always Test in Sandbox First
```bash
# In .env file
EBAY_SANDBOX=true
```

Run your entire workflow in sandbox mode before going to production.

### 2. Start Small
Test with 3-5 products first:
```bash
# Create a small test file
head -6 B1.csv > test.csv  # Header + 5 products
python run_workflow.py test.csv
```

### 3. Review Enriched Data
Before publishing, check the enriched CSV:
- Verify titles are accurate
- Confirm pricing (should be 50% of MSRP)
- Review descriptions
- Check categories

### 4. Monitor Results
- Save the results JSON files
- Keep track of offer IDs
- Review any failed items

### 5. Batch Processing
For large inventories, process in batches:
- 25 items per batch (eBay API limit)
- The workflow automatically handles batching

## Pricing Strategy

**Current Policy: 50% of MSRP**

All products are automatically priced at 50% of their retail price:

| Product MSRP | Your Price (50%) |
|--------------|------------------|
| $100         | $50              |
| $599         | $299.50          |
| $349         | $174.50          |

To change this percentage, edit `agent_enricher.py` line 237:
```python
suggested = retail_price * 0.50  # Change 0.50 to your percentage
```

## Advanced Usage

### Custom CSV Processing

```python
from integrated_workflow import IntegratedEbayWorkflow

workflow = IntegratedEbayWorkflow(
    ebay_client_id="your_id",
    ebay_client_secret="your_secret",
    openai_api_key="your_key",
    sandbox=True
)

results = workflow.enrich_and_list(
    input_csv="custom_products.csv",
    enriched_csv="custom_enriched.csv",
    create_listings=True,
    batch_size=25
)

# Print detailed report
workflow.print_summary_report(results)
```

### Programmatic Listing

```python
from agent_enricher import AgentBasedEnricher
from integrated_workflow import IntegratedEbayWorkflow

# Enrich first
enricher = AgentBasedEnricher()
product = enricher.enrich_product(
    sku="CUSTOM-001",
    brand="Apple",
    model="MacBook Pro",
    condition="very good"
)

# Then list to eBay
workflow = IntegratedEbayWorkflow(...)
# ... convert to inventory item and publish
```

## Getting Help

### Check Logs
```bash
tail -f integrated_workflow.log
```

### Verify Configuration
```bash
python -c "
from integrated_workflow import *
import os
print('OpenAI:', '✓' if os.getenv('OPENAI_API_KEY') else '✗')
print('eBay ID:', '✓' if os.getenv('EBAY_CLIENT_ID') else '✗')
print('eBay Secret:', '✓' if os.getenv('EBAY_CLIENT_SECRET') else '✗')
"
```

### Test eBay Connection
```bash
python -c "
from ebay_autolister import EbayAPI
import os
api = EbayAPI(
    os.getenv('EBAY_CLIENT_ID'),
    os.getenv('EBAY_CLIENT_SECRET'),
    sandbox=True
)
print('Auth:', '✓' if api.authenticate() else '✗')
"
```

## Support Resources

- **eBay Developer Portal**: https://developer.ebay.com/
- **eBay Sandbox**: https://sandbox.ebay.com/
- **OpenAI Documentation**: https://platform.openai.com/docs
- **This Project's README**: See `AGENT_WORKFLOW_README.md`

## Summary

1. ✅ Set up `.env` with eBay credentials
2. ✅ Prepare your CSV file
3. ✅ Run: `python run_workflow.py`
4. ✅ Choose option 3 to publish
5. ✅ Confirm when prompted
6. ✅ Review the summary report
7. ✅ Check your eBay Seller Hub

Your enriched products with 50% MSRP pricing will be live on eBay!
