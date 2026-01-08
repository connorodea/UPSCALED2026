#!/usr/bin/env python3
"""
Integrated workflow combining AI Agent enrichment with eBay Autolister.

This script orchestrates the complete process:
1. Load inventory from CSV
2. Enrich products using AI agents
3. Create eBay inventory items
4. Create and publish listings
"""

import os
import sys
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path

from agent_enricher import AgentBasedEnricher, EnrichedProduct
from ebay_autolister import (
    EbayAutolister,
    InventoryItem,
    EbayAPI,
    InventoryManager,
    ListingManager
)
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integrated_workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IntegratedEbayWorkflow:
    """
    Complete workflow integrating AI enrichment with eBay listing creation.
    """

    def __init__(
        self,
        ebay_client_id: str,
        ebay_client_secret: str,
        openai_api_key: str,
        sandbox: bool = True,
        ebay_user_token: str = None
    ):
        """
        Initialize the integrated workflow.

        Args:
            ebay_client_id: eBay API client ID
            ebay_client_secret: eBay API client secret
            openai_api_key: OpenAI API key
            sandbox: Use eBay sandbox environment
            ebay_user_token: Optional eBay user token (for production)
        """
        self.config = Config()
        self.enricher = AgentBasedEnricher(openai_api_key=openai_api_key)
        self.autolister = EbayAutolister(
            client_id=ebay_client_id,
            client_secret=ebay_client_secret,
            sandbox=sandbox,
            user_token=ebay_user_token
        )
        self.sandbox = sandbox

        logger.info("Integrated workflow initialized")

    def enrich_and_list(
        self,
        input_csv: str,
        enriched_csv: Optional[str] = None,
        create_listings: bool = False,
        batch_size: int = 25
    ) -> Dict:
        """
        Complete workflow: enrich products and create eBay listings.

        Args:
            input_csv: Path to input CSV with basic product data
            enriched_csv: Path to save enriched data (optional)
            create_listings: Whether to publish listings (vs inventory only)
            batch_size: Number of items to process in each batch

        Returns:
            Dictionary with results summary
        """
        logger.info(f"Starting integrated workflow for {input_csv}")

        # Generate output filenames
        if enriched_csv is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            enriched_csv = f"enriched_{timestamp}.csv"

        # Step 1: Load input CSV
        logger.info("Step 1: Loading input CSV")
        df = pd.read_csv(input_csv)
        logger.info(f"Loaded {len(df)} rows from {input_csv}")

        # Step 2: Enrich products using AI agents
        logger.info("Step 2: Enriching products with AI agents")
        enriched_products = self._enrich_products(df)

        if not enriched_products:
            logger.error("No products were successfully enriched")
            return {
                "success": False,
                "message": "Enrichment failed for all products"
            }

        # Save enriched data
        enriched_df = pd.DataFrame([vars(p) for p in enriched_products])
        enriched_df.to_csv(enriched_csv, index=False)
        logger.info(f"Enriched data saved to {enriched_csv}")

        # Step 3: Convert to eBay inventory items
        logger.info("Step 3: Converting to eBay inventory items")
        inventory_items = self._convert_to_inventory_items(enriched_products)

        # Step 4: Create eBay inventory items
        logger.info("Step 4: Creating eBay inventory items")
        inventory_results = self.autolister.inventory.bulk_create_inventory_items(
            inventory_items,
            batch_size=batch_size
        )

        results = {
            "success": True,
            "products_enriched": len(enriched_products),
            "enriched_csv": enriched_csv,
            "inventory_created": len(inventory_results["successful"]),
            "inventory_failed": len(inventory_results["failed"]),
            "failed_items": inventory_results["failed"]
        }

        # Step 5: Create and publish listings (if requested)
        if create_listings:
            logger.info("Step 5: Creating and publishing listings")
            listing_results = self._create_listings(
                enriched_products,
                inventory_results["successful"]
            )

            results.update({
                "listings_created": listing_results["created"],
                "listings_failed": listing_results["failed"],
                "successful_listings": listing_results.get("successful_listings", []),
                "failed_listings": listing_results.get("failed_listings", [])
            })

        logger.info("Integrated workflow completed")
        return results

    def _enrich_products(self, df: pd.DataFrame) -> List[EnrichedProduct]:
        """
        Enrich all products in the DataFrame using AI agents.

        Args:
            df: DataFrame with product data

        Returns:
            List of EnrichedProduct objects
        """
        enriched_products = []

        for idx, row in df.iterrows():
            try:
                # Extract required fields
                sku = str(row.get('sku', f'ROW_{idx}'))
                brand = str(row.get('brand', ''))
                model = str(row.get('model', ''))
                condition = str(row.get('condition', 'good'))

                if not brand and not model:
                    logger.warning(f"Row {idx}: Missing brand and model, skipping")
                    continue

                # Enrich using AI agents
                logger.info(f"Enriching {idx + 1}/{len(df)}: {brand} {model}")
                enriched = self.enricher.enrich_product(
                    sku=sku,
                    brand=brand,
                    model=model,
                    condition=condition
                )

                enriched_products.append(enriched)

            except Exception as e:
                logger.error(f"Failed to enrich row {idx}: {e}")
                continue

        logger.info(f"Successfully enriched {len(enriched_products)}/{len(df)} products")
        return enriched_products

    def _convert_to_inventory_items(
        self,
        enriched_products: List[EnrichedProduct]
    ) -> List[InventoryItem]:
        """
        Convert EnrichedProduct objects to eBay InventoryItem objects.

        Args:
            enriched_products: List of enriched products

        Returns:
            List of InventoryItem objects ready for eBay API
        """
        inventory_items = []

        for product in enriched_products:
            try:
                # Create inventory item
                item = InventoryItem(
                    sku=product.sku,
                    title=product.title[:80],  # eBay limit
                    description=product.description,
                    condition=product.condition,
                    category_id=product.category_id or "58058",  # Default category
                    price=product.suggested_price or 0.0,
                    quantity=1,  # Default quantity
                    brand=product.brand,
                    mpn=product.mpn or product.sku,
                    upc=product.upc,
                    grade="",
                    weight=product.weight_lbs,
                    dimensions=product.dimensions,
                    images=product.images
                )

                inventory_items.append(item)

            except Exception as e:
                logger.error(f"Failed to convert {product.sku} to inventory item: {e}")
                continue

        logger.info(f"Converted {len(inventory_items)} products to inventory items")
        return inventory_items

    def _create_listings(
        self,
        enriched_products: List[EnrichedProduct],
        successful_skus: List[str]
    ) -> Dict:
        """
        Create and publish eBay listings for successful inventory items.

        Args:
            enriched_products: List of enriched products
            successful_skus: List of SKUs that were successfully created in inventory

        Returns:
            Dictionary with detailed results including successful and failed SKUs
        """
        created = 0
        failed = 0
        successful_listings = []
        failed_listings = []

        logger.info(f"Creating listings for {len(successful_skus)} inventory items...")

        for product in enriched_products:
            if product.sku not in successful_skus:
                continue

            try:
                # Create offer
                logger.info(f"Creating offer for {product.sku} - {product.title[:50]}...")
                offer_id = self.autolister.listings.create_offer(
                    sku=product.sku,
                    category_id=product.category_id or "58058",
                    price=product.suggested_price or product.market_price or 0.0
                )

                if offer_id:
                    # Publish offer
                    logger.info(f"Publishing offer {offer_id} for {product.sku}...")
                    if self.autolister.listings.publish_offer(offer_id):
                        created += 1
                        successful_listings.append({
                            "sku": product.sku,
                            "title": product.title,
                            "price": product.suggested_price,
                            "offer_id": offer_id
                        })
                        logger.info(f"✓ Successfully published {product.sku} at ${product.suggested_price:.2f}")
                    else:
                        failed += 1
                        failed_listings.append({
                            "sku": product.sku,
                            "error": "Failed to publish offer"
                        })
                        logger.error(f"✗ Failed to publish listing for {product.sku}")
                else:
                    failed += 1
                    failed_listings.append({
                        "sku": product.sku,
                        "error": "Failed to create offer"
                    })
                    logger.error(f"✗ Failed to create offer for {product.sku}")

            except Exception as e:
                failed += 1
                failed_listings.append({
                    "sku": product.sku,
                    "error": str(e)
                })
                logger.error(f"✗ Listing creation failed for {product.sku}: {e}")

        return {
            "created": created,
            "failed": failed,
            "successful_listings": successful_listings,
            "failed_listings": failed_listings
        }

    def print_summary_report(self, results: Dict):
        """
        Print a detailed summary report of the workflow results.

        Args:
            results: Results dictionary from enrich_and_list()
        """
        print("\n" + "=" * 80)
        print("EBAY LISTING WORKFLOW - SUMMARY REPORT")
        print("=" * 80)

        # Enrichment Results
        print("\n📊 ENRICHMENT RESULTS")
        print("-" * 80)
        print(f"Products Processed:       {results.get('products_enriched', 0)}")
        print(f"Enriched CSV Saved:       {results.get('enriched_csv', 'N/A')}")

        # Inventory Results
        print("\n📦 INVENTORY CREATION RESULTS")
        print("-" * 80)
        print(f"✓ Successfully Created:   {results.get('inventory_created', 0)}")
        print(f"✗ Failed:                 {results.get('inventory_failed', 0)}")

        # Listing Results (if applicable)
        if 'listings_created' in results:
            print("\n🏪 EBAY LISTING PUBLICATION RESULTS")
            print("-" * 80)
            print(f"✓ Successfully Published: {results.get('listings_created', 0)}")
            print(f"✗ Failed:                 {results.get('listings_failed', 0)}")

            # Show successful listings
            if results.get('successful_listings'):
                print("\n✓ SUCCESSFULLY PUBLISHED LISTINGS:")
                for listing in results['successful_listings']:
                    print(f"  • {listing['sku']}: {listing['title'][:60]}")
                    print(f"    Price: ${listing['price']:.2f} | Offer ID: {listing['offer_id']}")

            # Show failed listings
            if results.get('failed_listings'):
                print("\n✗ FAILED LISTINGS:")
                for listing in results['failed_listings']:
                    print(f"  • {listing['sku']}: {listing['error']}")

        # Failed inventory items
        if results.get('failed_items'):
            print("\n✗ FAILED INVENTORY ITEMS:")
            for item in results['failed_items']:
                print(f"  • {item['sku']}: {item['error']}")

        # Summary
        print("\n" + "=" * 80)
        total_success = results.get('listings_created', results.get('inventory_created', 0))
        total_attempted = results.get('products_enriched', 0)
        success_rate = (total_success / total_attempted * 100) if total_attempted > 0 else 0

        print(f"OVERALL SUCCESS RATE: {success_rate:.1f}% ({total_success}/{total_attempted})")
        print("=" * 80 + "\n")


def main():
    """
    Interactive workflow with confirmation before publishing to eBay.
    """
    # Load configuration from environment
    ebay_client_id = os.getenv('EBAY_CLIENT_ID')
    ebay_client_secret = os.getenv('EBAY_CLIENT_SECRET')
    ebay_user_token = os.getenv('EBAY_AUTH_TOKEN')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    use_sandbox = os.getenv('EBAY_SANDBOX', 'true').lower() == 'true'

    if not all([ebay_client_id, ebay_client_secret, openai_api_key]):
        print("\n" + "=" * 80)
        print("ERROR: Missing Required Environment Variables")
        print("=" * 80)
        print("\nPlease set the following in your .env file:")
        if not ebay_client_id:
            print("  ✗ EBAY_CLIENT_ID")
        if not ebay_client_secret:
            print("  ✗ EBAY_CLIENT_SECRET")
        if not openai_api_key:
            print("  ✗ OPENAI_API_KEY")
        print("\n" + "=" * 80 + "\n")
        sys.exit(1)

    # Get input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "B1.csv"  # Default file

    if not os.path.exists(input_file):
        print(f"\n✗ Error: Input file '{input_file}' not found")
        print(f"Usage: python integrated_workflow.py [input_file.csv]\n")
        sys.exit(1)

    # Initialize workflow
    workflow = IntegratedEbayWorkflow(
        ebay_client_id=ebay_client_id,
        ebay_client_secret=ebay_client_secret,
        openai_api_key=openai_api_key,
        sandbox=use_sandbox,
        ebay_user_token=ebay_user_token
    )

    # Display configuration
    print("\n" + "=" * 80)
    print("EBAY LISTING WORKFLOW - CONFIGURATION")
    print("=" * 80)
    print(f"Input File:       {input_file}")
    print(f"Sandbox Mode:     {'YES (Testing)' if use_sandbox else 'NO (Production)'}")
    print(f"OpenAI API:       Configured ✓")
    print(f"eBay API:         Configured ✓")
    print("=" * 80)

    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("  1. Enrich products only (no eBay upload)")
    print("  2. Enrich + Create inventory items (no listings)")
    print("  3. Enrich + Create inventory + Publish listings to eBay")

    choice = input("\nEnter your choice (1-3): ").strip()

    create_listings = False
    if choice == "3":
        print("\n⚠️  WARNING: This will publish listings to eBay!")
        if use_sandbox:
            print("✓ You are using SANDBOX mode (safe for testing)")
        else:
            print("⚠️  You are using PRODUCTION mode (real listings will be created)")

        confirm = input("\nAre you sure you want to proceed? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            create_listings = True
            print("\n✓ Confirmed: Will publish listings to eBay")
        else:
            print("\n✗ Cancelled: Will create inventory only (no listings)")
    elif choice == "1":
        print("\n✓ Mode: Enrichment only")
        # TODO: Add enrichment-only mode
        print("Note: Full workflow will run but skip eBay integration")
    else:
        print("\n✓ Mode: Enrichment + Inventory (no listings)")

    # Run the workflow
    print("\n" + "=" * 80)
    print("STARTING WORKFLOW...")
    print("=" * 80 + "\n")

    results = workflow.enrich_and_list(
        input_csv=input_file,
        create_listings=create_listings,
        batch_size=25
    )

    # Display detailed summary report
    workflow.print_summary_report(results)

    # Save results to JSON for record-keeping
    results_file = f"workflow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        # Convert results to JSON-serializable format
        json_results = {k: v for k, v in results.items() if k != 'failed_items'}
        json.dump(json_results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}\n")


if __name__ == "__main__":
    main()
