#!/usr/bin/env python3
"""
Example usage scripts for AI Agent-based eBay listing enrichment.

Run these examples to test the agent workflow.
"""

import os
import sys
from dotenv import load_dotenv
from agent_enricher import AgentBasedEnricher
from integrated_workflow import IntegratedEbayWorkflow

# Load environment variables
load_dotenv()


def example_1_single_product():
    """
    Example 1: Enrich a single product and display results.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Single Product Enrichment")
    print("="*60)

    # Initialize enricher
    enricher = AgentBasedEnricher()

    # Enrich a product
    print("\nEnriching product: Apple iPad Air 5th Gen (Like New)")
    product = enricher.enrich_product(
        sku="DEMO-001",
        brand="Apple",
        model="iPad Air 5th Gen",
        condition="like new"
    )

    # Display results
    print("\n" + "-"*60)
    print("ENRICHED PRODUCT DATA")
    print("-"*60)
    print(f"SKU:              {product.sku}")
    print(f"Title:            {product.title}")
    print(f"Category:         {product.category_name} ({product.category_id})")
    print(f"Retail Price:     ${product.retail_price:.2f}")
    print(f"Market Price:     ${product.market_price:.2f}")
    print(f"Suggested Price:  ${product.suggested_price:.2f}")
    print(f"Weight:           {product.weight_lbs} lbs")
    print(f"Dimensions:       {product.dimensions}")
    print(f"MPN:              {product.mpn}")
    print(f"UPC:              {product.upc}")
    print(f"Confidence:       {product.confidence_score:.2f}")
    print(f"\nItem Specifics:   {product.item_specifics}")
    print(f"\nDescription Preview:")
    print(f"{product.description[:200]}...")
    print("-"*60)


def example_2_csv_enrichment():
    """
    Example 2: Enrich products from CSV file.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: CSV File Enrichment")
    print("="*60)

    # Check if sample file exists
    sample_file = "sample_products.csv"
    if not os.path.exists(sample_file):
        print(f"\nCreating sample CSV file: {sample_file}")
        create_sample_csv(sample_file)

    # Initialize enricher
    enricher = AgentBasedEnricher()

    # Enrich CSV
    print(f"\nEnriching products from: {sample_file}")
    output_file = "sample_products_enriched.csv"

    df = enricher.enrich_csv(
        input_csv=sample_file,
        output_csv=output_file,
        sku_col="sku",
        brand_col="brand",
        model_col="model",
        condition_col="condition"
    )

    print(f"\n✓ Enrichment complete!")
    print(f"  Input:  {sample_file}")
    print(f"  Output: {output_file}")
    print(f"  Products enriched: {len(df)}")


def example_3_integrated_workflow():
    """
    Example 3: Full integrated workflow (enrichment + eBay listing).
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Integrated Workflow (Enrichment + eBay)")
    print("="*60)

    # Check environment variables
    ebay_client_id = os.getenv('EBAY_CLIENT_ID')
    ebay_client_secret = os.getenv('EBAY_CLIENT_SECRET')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not all([ebay_client_id, ebay_client_secret, openai_api_key]):
        print("\n✗ Missing required environment variables:")
        if not ebay_client_id:
            print("  - EBAY_CLIENT_ID")
        if not ebay_client_secret:
            print("  - EBAY_CLIENT_SECRET")
        if not openai_api_key:
            print("  - OPENAI_API_KEY")
        print("\nPlease set these in your .env file")
        return

    # Check if sample file exists
    sample_file = "sample_products.csv"
    if not os.path.exists(sample_file):
        print(f"\nCreating sample CSV file: {sample_file}")
        create_sample_csv(sample_file)

    # Initialize workflow
    workflow = IntegratedEbayWorkflow(
        ebay_client_id=ebay_client_id,
        ebay_client_secret=ebay_client_secret,
        openai_api_key=openai_api_key,
        sandbox=True  # Use sandbox for testing
    )

    # Run workflow
    print(f"\nProcessing: {sample_file}")
    print("Sandbox mode: YES (safe for testing)")
    print("Creating listings: NO (inventory only)")

    results = workflow.enrich_and_list(
        input_csv=sample_file,
        create_listings=False,  # Set True to publish
        batch_size=5
    )

    # Display results
    print("\n" + "-"*60)
    print("WORKFLOW RESULTS")
    print("-"*60)
    print(f"✓ Products enriched:      {results.get('products_enriched', 0)}")
    print(f"✓ Enriched CSV:           {results.get('enriched_csv', 'N/A')}")
    print(f"✓ Inventory created:      {results.get('inventory_created', 0)}")
    print(f"✗ Inventory failed:       {results.get('inventory_failed', 0)}")

    if results.get('failed_items'):
        print(f"\nFailed items:")
        for item in results['failed_items']:
            print(f"  - {item['sku']}: {item['error']}")

    print("-"*60)


def example_4_custom_pricing():
    """
    Example 4: Demonstrate different pricing strategies by condition.
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Pricing Analysis by Condition")
    print("="*60)

    enricher = AgentBasedEnricher()

    # Test same product at different conditions
    conditions = ["like new", "very good", "good", "acceptable", "salvage"]
    base_product = ("Apple", "MacBook Pro 13-inch M2")

    print(f"\nProduct: {base_product[0]} {base_product[1]}")
    print(f"Analyzing pricing for different conditions...\n")

    print(f"{'Condition':<15} {'Suggested Price':<20} {'vs Retail'}")
    print("-" * 60)

    for condition in conditions:
        product = enricher.enrich_product(
            sku=f"TEST-{condition.upper().replace(' ', '_')}",
            brand=base_product[0],
            model=base_product[1],
            condition=condition
        )

        discount = 0
        if product.retail_price > 0:
            discount = ((product.retail_price - product.suggested_price)
                       / product.retail_price * 100)

        print(f"{condition:<15} ${product.suggested_price:<18.2f} "
              f"-{discount:.0f}% off retail")


def create_sample_csv(filename: str):
    """Create a sample CSV file for testing."""
    import pandas as pd

    sample_data = [
        {
            "sku": "SAMPLE-001",
            "brand": "Apple",
            "model": "iPad Air 5th Gen",
            "condition": "like new"
        },
        {
            "sku": "SAMPLE-002",
            "brand": "Nintendo",
            "model": "Switch OLED",
            "condition": "very good"
        },
        {
            "sku": "SAMPLE-003",
            "brand": "Samsung",
            "model": "Galaxy S23",
            "condition": "good"
        }
    ]

    df = pd.DataFrame(sample_data)
    df.to_csv(filename, index=False)
    print(f"✓ Created {filename} with {len(df)} sample products")


def main():
    """
    Run examples based on command line argument.
    """
    print("\n" + "="*60)
    print("AI AGENT-BASED EBAY LISTING ENRICHMENT - EXAMPLES")
    print("="*60)

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
    else:
        print("\nAvailable examples:")
        print("  1 - Single product enrichment")
        print("  2 - CSV file enrichment")
        print("  3 - Integrated workflow (enrichment + eBay)")
        print("  4 - Pricing analysis by condition")
        print("  all - Run all examples")

        example_num = input("\nEnter example number (1-4 or 'all'): ").strip()

    if example_num == "1":
        example_1_single_product()
    elif example_num == "2":
        example_2_csv_enrichment()
    elif example_num == "3":
        example_3_integrated_workflow()
    elif example_num == "4":
        example_4_custom_pricing()
    elif example_num.lower() == "all":
        example_1_single_product()
        example_2_csv_enrichment()
        example_3_integrated_workflow()
        example_4_custom_pricing()
    else:
        print(f"\n✗ Invalid example number: {example_num}")
        print("Please choose 1-4 or 'all'")
        sys.exit(1)

    print("\n" + "="*60)
    print("Example complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
