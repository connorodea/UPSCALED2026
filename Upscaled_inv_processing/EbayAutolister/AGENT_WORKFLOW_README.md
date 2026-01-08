# AI Agent-Based eBay Listing Enrichment

This system uses the OpenAI Agents Python SDK to automatically gather missing listing details for eBay products through an intelligent multi-agent workflow.

## Overview

The AI agent workflow enriches your product listings by:

1. **Researching Products** - Gathers specifications, features, and identifiers
2. **Analyzing Pricing** - Determines competitive pricing based on condition
3. **Creating Content** - Generates SEO-optimized titles and descriptions
4. **Extracting Specifics** - Identifies relevant eBay item specifics
5. **Estimating Shipping** - Calculates weight and dimensions

## Architecture

### Multi-Agent System

The system uses 4 specialized AI agents:

```
┌─────────────────────────────────────────────────────┐
│          Enrichment Coordinator Agent               │
│  (Orchestrates the overall enrichment workflow)     │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────┼───────────┬───────────────┐
       │           │           │               │
       ▼           ▼           ▼               ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Product  │ │ Pricing  │ │ Listing  │ │   Tools      │
│Researcher│ │Specialist│ │  Writer  │ │(Web Search,  │
│          │ │          │ │          │ │ Category,    │
│          │ │          │ │          │ │ Description) │
└──────────┘ └──────────┘ └──────────┘ └──────────────┘
```

### Agent Responsibilities

1. **Enrichment Coordinator**
   - Manages workflow orchestration
   - Routes tasks to specialized agents
   - Compiles final enriched data

2. **Product Researcher**
   - Web search for product information
   - Gathers specifications and features
   - Finds product identifiers (UPC, EAN, MPN)
   - Collects product images

3. **Pricing Specialist**
   - Analyzes current market conditions
   - Applies condition-based depreciation
   - Recommends competitive pricing
   - Provides price ranges

4. **Listing Writer**
   - Creates SEO-optimized titles
   - Writes compelling descriptions
   - Extracts eBay item specifics
   - Formats HTML content

## Installation

### 1. Install Dependencies

```bash
cd EbayAutolister
pip install -r requirements.txt
```

This will install:
- `openai-agents` - OpenAI Agents SDK
- `openai` - OpenAI API client
- `pandas` - Data processing
- Other required packages

### 2. Set Up Environment Variables

Create or update your `.env` file:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# eBay Configuration
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
EBAY_SANDBOX=true

# Optional: Model Configuration
OPENAI_MODEL=gpt-4o
```

## Usage

### Option 1: Integrated Workflow (Recommended)

Use the complete workflow that enriches products and creates eBay listings:

```python
from integrated_workflow import IntegratedEbayWorkflow

# Initialize
workflow = IntegratedEbayWorkflow(
    ebay_client_id="your_client_id",
    ebay_client_secret="your_client_secret",
    openai_api_key="your_openai_key",
    sandbox=True
)

# Process CSV file
results = workflow.enrich_and_list(
    input_csv="products.csv",
    enriched_csv="products_enriched.csv",
    create_listings=False,  # Set True to publish
    batch_size=25
)

print(f"Enriched: {results['products_enriched']}")
print(f"Created: {results['inventory_created']}")
```

### Option 2: Agent Enricher Only

Use just the AI agent enrichment without eBay integration:

```python
from agent_enricher import AgentBasedEnricher

# Initialize
enricher = AgentBasedEnricher(openai_api_key="your_key")

# Enrich single product
product = enricher.enrich_product(
    sku="ITEM-001",
    brand="Apple",
    model="iPad Air 5th Gen",
    condition="like new"
)

print(f"Title: {product.title}")
print(f"Price: ${product.suggested_price}")
print(f"Category: {product.category_name}")

# Or enrich from CSV
enricher.enrich_csv(
    input_csv="products.csv",
    output_csv="enriched_products.csv",
    sku_col="sku",
    brand_col="brand",
    model_col="model",
    condition_col="condition"
)
```

### Command Line Usage

```bash
# Run integrated workflow
python integrated_workflow.py

# Or run agent enricher only
python agent_enricher.py
```

## Input CSV Format

Your input CSV should have these minimum columns:

| Column    | Description              | Example           |
|-----------|--------------------------|-------------------|
| sku       | Unique SKU               | ITEM-001          |
| brand     | Product brand            | Apple             |
| model     | Product model            | iPad Air 5th Gen  |
| condition | Item condition           | like new          |

**Supported Conditions:**
- `like new` - Minimal wear
- `very good` - Light wear
- `good` - Normal wear
- `acceptable` - Heavy wear
- `salvage` - Parts/repair

## Output Data

The enriched CSV will contain all input columns PLUS:

### Product Information
- `title` - SEO-optimized product title
- `description` - Detailed HTML description
- `category_id` - eBay category ID
- `category_name` - Category name/path

### Pricing
- `retail_price` - Original MSRP
- `market_price` - Current market average
- `suggested_price` - Recommended listing price

### Identifiers
- `upc` - Universal Product Code
- `ean` - European Article Number
- `isbn` - ISBN (for books)
- `mpn` - Manufacturer Part Number

### Shipping
- `weight_lbs` - Package weight in pounds
- `dimensions` - Length, width, height in inches

### Additional
- `item_specifics` - eBay item specifics (JSON)
- `images` - Product image URLs (array)
- `confidence_score` - Enrichment confidence (0-1)
- `sources` - Data source URLs

## Examples

### Example 1: Enrich and Preview

```python
from agent_enricher import AgentBasedEnricher

enricher = AgentBasedEnricher()

# Enrich a product
product = enricher.enrich_product(
    sku="TEST-001",
    brand="Nintendo",
    model="Switch OLED",
    condition="very good"
)

# Review results
print(f"Title: {product.title}")
print(f"Category: {product.category_name} ({product.category_id})")
print(f"Suggested Price: ${product.suggested_price:.2f}")
print(f"Weight: {product.weight_lbs} lbs")
print(f"Dimensions: {product.dimensions}")
print(f"Item Specifics: {product.item_specifics}")
```

### Example 2: Full Workflow with Listing

```python
from integrated_workflow import IntegratedEbayWorkflow
import os

workflow = IntegratedEbayWorkflow(
    ebay_client_id=os.getenv('EBAY_CLIENT_ID'),
    ebay_client_secret=os.getenv('EBAY_CLIENT_SECRET'),
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    sandbox=True
)

results = workflow.enrich_and_list(
    input_csv="my_products.csv",
    create_listings=True,  # Publish to eBay
    batch_size=25
)

# Check results
if results['success']:
    print(f"✓ Enriched {results['products_enriched']} products")
    print(f"✓ Created {results['inventory_created']} inventory items")
    print(f"✓ Published {results['listings_created']} listings")
else:
    print(f"✗ Workflow failed: {results['message']}")
```

### Example 3: Batch Processing

```python
from agent_enricher import AgentBasedEnricher
import pandas as pd

enricher = AgentBasedEnricher()

# Load your inventory
df = pd.read_csv("inventory.csv")

enriched_products = []
for idx, row in df.iterrows():
    product = enricher.enrich_product(
        sku=row['sku'],
        brand=row['brand'],
        model=row['model'],
        condition=row['condition']
    )
    enriched_products.append(product)

    print(f"Progress: {idx+1}/{len(df)}")

# Save results
results_df = pd.DataFrame([vars(p) for p in enriched_products])
results_df.to_csv("enriched_inventory.csv", index=False)
```

## How It Works

### 1. Agent Workflow

When you enrich a product:

```
1. Coordinator receives request →
2. Hands off to Product Researcher →
   - Searches web for product info
   - Identifies category
   - Estimates shipping details
3. Hands off to Pricing Specialist →
   - Analyzes market pricing
   - Applies condition adjustments
   - Recommends competitive price
4. Hands off to Listing Writer →
   - Creates SEO-optimized title
   - Generates detailed description
   - Extracts item specifics
5. Coordinator compiles complete data →
6. Returns EnrichedProduct object
```

### 2. Tool Functions

The agents use these specialized tools:

- `web_search_product()` - Search for product information
- `get_ebay_category()` - Determine best eBay category
- `analyze_market_pricing()` - Calculate competitive pricing
- `generate_product_description()` - Create listing content
- `extract_item_specifics()` - Format eBay item specifics
- `estimate_shipping_details()` - Calculate weight/dimensions

### 3. Integration with eBay

The enriched data flows into the eBay autolister:

```
EnrichedProduct → InventoryItem → eBay Inventory API → Offer → Published Listing
```

## Configuration

### Agent Settings

Customize agent behavior by modifying `agent_enricher.py`:

```python
# In create_coordinator_agent()
return Agent(
    name="Enrichment Coordinator",
    model="gpt-4o",  # Change model
    instructions="...",  # Customize instructions
    handoffs=[researcher, pricer, writer]
)
```

### Pricing Strategy

**Default Pricing Policy: 50% of MSRP**

All products are priced at 50% of their retail/MSRP price, regardless of condition.

Example:
- Product MSRP: $100
- Your listing price: $50 (50% of MSRP)

This is configured in the `analyze_market_pricing()` function in `agent_enricher.py`. To change this percentage, modify line 237:

```python
suggested = retail_price * 0.50  # Change 0.50 to your desired percentage
```

## Troubleshooting

### Common Issues

**1. Missing OPENAI_API_KEY**
```
Error: OPENAI_API_KEY must be set
```
Solution: Set your OpenAI API key in `.env` or environment

**2. Agent Workflow Timeout**
```
Max turns reached (20)
```
Solution: Increase `max_turns` in `Runner.run_sync()` call

**3. Low Confidence Scores**
```
Confidence: 0.3
```
Solution: Product may need more specific brand/model information

**4. Missing Category**
```
category_id: "58058" (default)
```
Solution: Provide more product context for better categorization

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance

### Timing

Typical enrichment times per product:
- Simple products (known brands): 5-10 seconds
- Complex products: 10-20 seconds
- Batch of 25 products: 3-7 minutes

### Cost Estimation

Using OpenAI GPT-4o:
- Per product: ~$0.02 - $0.05
- 100 products: ~$2 - $5
- 1000 products: ~$20 - $50

Tips to reduce costs:
- Use GPT-4o-mini for simpler tasks
- Cache common product lookups
- Batch similar products

## Best Practices

1. **Start Small** - Test with 5-10 products first
2. **Review Output** - Check enriched data before publishing
3. **Use Sandbox** - Test eBay integration in sandbox mode
4. **Monitor Costs** - Track OpenAI API usage
5. **Validate Data** - Verify critical fields (price, category)
6. **Handle Errors** - Implement retry logic for failures

## Advanced Usage

### Custom Tools

Add your own tools to agents:

```python
from agents import function_tool

@function_tool
def check_inventory_database(sku: str) -> Dict:
    """Look up existing inventory data"""
    # Your custom logic
    return {"in_stock": True, "location": "Warehouse A"}

# Add to agent
researcher = Agent(
    name="Product Researcher",
    tools=[web_search_product, check_inventory_database]
)
```

### Custom Agents

Create specialized agents for your needs:

```python
def create_compliance_agent() -> Agent:
    """Agent that checks listing compliance"""
    return Agent(
        name="Compliance Checker",
        instructions="""
        Review listings for eBay policy compliance.
        Flag any prohibited items or language.
        Ensure condition descriptions are accurate.
        """,
        tools=[check_prohibited_items, validate_description]
    )
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review OpenAI Agents SDK docs: https://github.com/openai/openai-agents-python
3. Check eBay API documentation
4. Enable debug logging for detailed error messages

## License

This implementation uses:
- OpenAI Agents SDK (MIT License)
- eBay API (see eBay Developer Agreement)
