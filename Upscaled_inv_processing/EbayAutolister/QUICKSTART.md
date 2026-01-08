# Quick Start Guide - AI Agent Workflow

Get started with AI-powered eBay listing enrichment in 5 minutes.

## Prerequisites

- Python 3.9+
- OpenAI API key
- eBay Developer account (optional, for full integration)

## Step 1: Install Dependencies

```bash
cd EbayAutolister
pip install -r requirements.txt
```

## Step 2: Configure Environment

Create `.env` file in the `EbayAutolister` directory:

```bash
# Required for agent enrichment
OPENAI_API_KEY=sk-your-openai-api-key-here

# Required only for eBay integration
EBAY_CLIENT_ID=your-ebay-client-id
EBAY_CLIENT_SECRET=your-ebay-client-secret
EBAY_SANDBOX=true
```

## Step 3: Test with Examples

### Option A: Quick Test (Single Product)

```bash
python -c "
from agent_enricher import AgentBasedEnricher
enricher = AgentBasedEnricher()
product = enricher.enrich_product(
    sku='TEST-001',
    brand='Apple',
    model='iPad Air',
    condition='like new'
)
print(f'Title: {product.title}')
print(f'Price: \${product.suggested_price}')
print(f'Category: {product.category_name}')
"
```

### Option B: Run Interactive Examples

```bash
python example_agent_usage.py
```

Then select an example to run (1-4).

### Option C: Process Your CSV

1. Prepare your CSV with columns: `sku`, `brand`, `model`, `condition`

2. Run enrichment:

```bash
python -c "
from agent_enricher import AgentBasedEnricher
enricher = AgentBasedEnricher()
enricher.enrich_csv(
    input_csv='your_products.csv',
    output_csv='enriched_products.csv'
)
"
```

## Step 4: Review Results

The enriched CSV will contain:
- Product titles
- eBay categories
- Market pricing
- Item specifics
- Shipping details
- Product descriptions

## Step 5: (Optional) Publish to eBay

If you have eBay credentials:

```bash
python integrated_workflow.py
```

This will:
1. Enrich your products
2. Create eBay inventory items
3. Optionally publish listings

## What's Next?

- Read `AGENT_WORKFLOW_README.md` for detailed documentation
- Customize agents in `agent_enricher.py`
- Adjust pricing strategies
- Add custom tools

## Troubleshooting

**"OPENAI_API_KEY is not set"**
- Make sure `.env` file exists in the correct directory
- Verify the API key is valid

**"No module named 'agents'"**
- Run: `pip install openai-agents`

**Agent workflow is slow**
- This is normal - each product takes 5-15 seconds
- Agents are making web searches and API calls

**Enrichment failed**
- Check your OpenAI API key is valid
- Ensure you have API credits available
- Try with a well-known product first (e.g., "Apple iPad")

## Cost Estimate

Using GPT-4o:
- Test run (5 products): ~$0.10 - $0.25
- Small batch (100 products): ~$2 - $5
- Large batch (1000 products): ~$20 - $50

## Support

See `AGENT_WORKFLOW_README.md` for:
- Detailed usage examples
- Architecture overview
- Advanced configuration
- Best practices
