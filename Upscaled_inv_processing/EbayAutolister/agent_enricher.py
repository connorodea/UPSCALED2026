#!/usr/bin/env python3
"""
AI Agent-based Product Enrichment System for eBay Listings
Uses OpenAI Agents SDK to create specialized agents for gathering missing listing details
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import pandas as pd
from agents import Agent, Runner, function_tool
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnrichedProduct:
    """Complete product data with all enrichment fields"""
    # Original fields
    sku: str
    brand: str
    model: str
    condition: str

    # Enriched fields
    title: str = ""
    description: str = ""
    category_id: str = ""
    category_name: str = ""

    # Pricing
    retail_price: float = 0.0
    market_price: float = 0.0
    suggested_price: float = 0.0

    # Enhanced pricing fields (from automated pricing engine)
    buy_it_now_price: float = 0.0
    min_offer_price: float = 0.0
    auto_accept_offer: float = 0.0
    auto_decline_offer: float = 0.0

    # Market intelligence
    avg_sold_price_30d: float = 0.0
    median_sold_price_30d: float = 0.0
    sold_count_30d: int = 0
    avg_active_price: float = 0.0
    active_listing_count: int = 0
    pricing_confidence: float = 0.0
    pricing_reasoning: str = ""

    # Product identifiers
    upc: str = ""
    ean: str = ""
    isbn: str = ""
    mpn: str = ""

    # Item specifics/aspects
    item_specifics: Dict[str, str] = None

    # Shipping
    weight_lbs: float = 0.0
    dimensions: Dict[str, float] = None  # length, width, height in inches

    # Additional details
    images: List[str] = None
    compatibility: str = ""
    warranty_info: str = ""

    # Metadata
    confidence_score: float = 0.0
    sources: List[str] = None

    def __post_init__(self):
        if self.item_specifics is None:
            self.item_specifics = {}
        if self.dimensions is None:
            self.dimensions = {"length": 10.0, "width": 10.0, "height": 10.0}
        if self.images is None:
            self.images = []
        if self.sources is None:
            self.sources = []


# ============================================================================
# TOOL FUNCTIONS - Available to all agents
# ============================================================================

@function_tool(strict_mode=False)
def web_search_product(brand: str, model: str) -> Dict[str, Any]:
    """
    Search the web for product information using OpenAI's web search capability.
    Returns general product details, specs, and pricing.

    Args:
        brand: Product brand/manufacturer
        model: Product model number or name

    Returns:
        Dictionary with product information
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    query = f"{brand} {model} specifications price reviews"
    prompt = f"""
Search for detailed information about: {brand} {model}

Return a JSON object with these fields:
{{
    "full_name": "Complete product name",
    "specifications": {{"key": "value"}},
    "retail_price": "Original MSRP price",
    "current_market_price": "Current average selling price",
    "key_features": ["feature1", "feature2"],
    "product_identifiers": {{"upc": "", "ean": "", "mpn": ""}},
    "source_urls": ["url1", "url2"]
}}

Focus on factual, verifiable information only.
"""

    try:
        # Note: This is a simplified example. Actual implementation would use
        # OpenAI's web search capabilities through the Responses API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        logger.info(f"Web search completed for {brand} {model}")
        return result
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return {}


@function_tool(strict_mode=False)
def get_ebay_category(product_name: str, brand: str) -> Dict[str, str]:
    """
    Determine the most appropriate eBay category for a product.

    Args:
        product_name: Full product name/description
        brand: Product brand

    Returns:
        Dictionary with category_id and category_name
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
You are an eBay category expert. Determine the BEST category for this product:
Product: {product_name}
Brand: {brand}

Consider eBay's category structure and return JSON:
{{
    "category_id": "numeric category ID",
    "category_name": "Full category path",
    "reasoning": "Why this category is best"
}}

Common eBay categories:
- Cell Phones & Smartphones: 9355
- Tablets & eBook Readers: 171485
- Apple Laptops: 111422
- Video Game Consoles: 139971
- Computers/Tablets & Networking: 58058
- Consumer Electronics: 293
- Collectibles: 1
- Clothing, Shoes & Accessories: 11450
- Home & Garden: 11700
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        logger.info(f"Category determined: {result.get('category_name', 'Unknown')}")
        return result
    except Exception as e:
        logger.error(f"Category lookup failed: {e}")
        return {"category_id": "58058", "category_name": "General", "reasoning": "Fallback"}


@function_tool(strict_mode=False)
def analyze_market_pricing(
    brand: str,
    model: str,
    condition: str,
    retail_price: float
) -> Dict[str, float]:
    """
    Analyze market pricing using eBay sold comps and active listings.
    Applies condition-based adjustments and caching.

    Args:
        brand: Product brand
        model: Product model
        condition: Item condition (like new, very good, good, acceptable, salvage)
        retail_price: Original retail price

    Returns:
        Dictionary with pricing recommendations
    """
    from ebay_pricing.pricing_engine import get_pricing_recommendation

    try:
        # Get intelligent pricing recommendation from our pricing engine
        pricing = get_pricing_recommendation(brand, model, condition, retail_price)

        logger.info(f"Pricing analysis complete: ${pricing.buy_it_now_price:.2f} (confidence: {pricing.confidence:.2f})")

        return {
            "current_market_avg": pricing.market_data.avg_sold_price if pricing.market_data else 0.0,
            "suggested_list_price": pricing.buy_it_now_price,
            "price_range_low": pricing.min_offer_price if pricing.min_offer_price else pricing.buy_it_now_price * 0.85,
            "price_range_high": pricing.buy_it_now_price,
            "min_offer_price": pricing.min_offer_price if pricing.min_offer_price else 0.0,
            "auto_accept_offer": pricing.auto_accept_offer if pricing.auto_accept_offer else 0.0,
            "auto_decline_offer": pricing.auto_decline_offer if pricing.auto_decline_offer else 0.0,
            "sold_count_30d": pricing.market_data.sold_count if pricing.market_data else 0,
            "active_listing_count": pricing.market_data.active_listing_count if pricing.market_data else 0,
            "avg_sold_price_30d": pricing.market_data.avg_sold_price if pricing.market_data else 0.0,
            "median_sold_price_30d": pricing.market_data.median_sold_price if pricing.market_data else 0.0,
            "avg_active_price": pricing.market_data.avg_active_price if pricing.market_data else 0.0,
            "confidence": pricing.confidence,
            "reasoning": pricing.reasoning
        }

    except Exception as e:
        logger.error(f"Pricing engine failed: {e}. Using fallback pricing.")
        # Fallback to current behavior (50% MSRP)
        suggested = retail_price * 0.50
        return {
            "current_market_avg": suggested,
            "suggested_list_price": suggested,
            "price_range_low": suggested * 0.90,
            "price_range_high": suggested * 1.10,
            "min_offer_price": suggested * 0.85,
            "auto_accept_offer": suggested * 0.95,
            "auto_decline_offer": suggested * 0.75,
            "sold_count_30d": 0,
            "active_listing_count": 0,
            "avg_sold_price_30d": 0.0,
            "median_sold_price_30d": 0.0,
            "avg_active_price": 0.0,
            "confidence": 0.2,
            "reasoning": f"Fallback pricing due to error: {str(e)}"
        }


@function_tool(strict_mode=False)
def generate_product_description(
    product_name: str,
    brand: str,
    model: str,
    condition: str,
    key_features: List[str],
    item_specifics: Dict[str, str]
) -> str:
    """
    Generate SEO-optimized, detailed product description for eBay listing.

    Args:
        product_name: Full product name
        brand: Product brand
        model: Product model
        condition: Item condition
        key_features: List of key product features
        item_specifics: Dictionary of item-specific attributes

    Returns:
        Formatted HTML description for eBay listing
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
Create a compelling, SEO-optimized eBay listing description for the following product.

Product: {product_name}
Brand: {brand}
Model: {model}
Condition: {condition}
Key Features: {', '.join(key_features) if key_features else 'N/A'}
Specifications: {json.dumps(item_specifics)}

IMPORTANT: Return ONLY the HTML description content itself, with NO introductory text, NO "Here's the description", NO conversational preamble. Start directly with the product description HTML.

Format the description with:
1. Engaging title hook
2. Key features and benefits (bullet points)
3. Detailed specifications
4. Condition details (be honest and specific)
5. What's included
6. Shipping and handling info placeholder

Use simple HTML formatting (h3, ul, li, strong, br).
Keep it professional, accurate, and buyer-focused.
Aim for 250-400 words.

Return ONLY the HTML description, nothing else.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        description = response.choices[0].message.content

        # Clean up any conversational preamble
        preambles = [
            "Here's the enriched product listing",
            "Here's a comprehensive overview",
            "Here's the enriched listing",
            "Here's the complete product information",
            "Here are the enriched details",
            "Here's the enriched information",
            "Here's the enriched data",
            "Here's a comprehensive product profile",
            "Here is the enriched",
            "Here are the enriched",
            "###"
        ]

        for preamble in preambles:
            if description.strip().startswith(preamble):
                # Find where the actual content starts (after first colon or newline)
                parts = description.split('\n', 2)
                if len(parts) > 1:
                    description = parts[1].strip()
                    if len(parts) > 2:
                        description = parts[2].strip()
                break

        logger.info(f"Description generated ({len(description)} chars)")
        return description
    except Exception as e:
        logger.error(f"Description generation failed: {e}")
        return f"<h3>{product_name}</h3><p>Brand: {brand}<br>Model: {model}<br>Condition: {condition}</p>"


@function_tool(strict_mode=False)
def extract_item_specifics(
    brand: str,
    model: str,
    category_id: str,
    specifications: Dict[str, Any]
) -> Dict[str, str]:
    """
    Extract and format item specifics/aspects for eBay category requirements.

    Args:
        brand: Product brand
        model: Product model
        category_id: eBay category ID
        specifications: Product specifications dictionary

    Returns:
        Dictionary of item specifics formatted for eBay
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
You are an eBay listing expert. Extract the most important item specifics for this product.

Product: {brand} {model}
eBay Category: {category_id}
Available Specs: {json.dumps(specifications)}

Return JSON with relevant item specifics. Common fields include:
{{
    "Brand": "",
    "Model": "",
    "Color": "",
    "Storage Capacity": "",
    "Screen Size": "",
    "Processor": "",
    "RAM Size": "",
    "Connectivity": "",
    "MPN": "",
    "Type": "",
    "Features": ""
}}

Only include fields that are relevant to this product category.
Use eBay-standard terminology and formats.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        logger.info(f"Item specifics extracted: {len(result)} fields")
        return result
    except Exception as e:
        logger.error(f"Item specifics extraction failed: {e}")
        return {"Brand": brand, "Model": model}


@function_tool(strict_mode=False)
def estimate_shipping_details(
    product_name: str,
    brand: str,
    model: str
) -> Dict[str, Any]:
    """
    Estimate shipping weight and dimensions based on product type.

    Args:
        product_name: Full product name
        brand: Product brand
        model: Product model

    Returns:
        Dictionary with weight and dimensions
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
Estimate typical shipping specifications for this product:
Product: {product_name}
Brand: {brand}
Model: {model}

Return JSON with realistic estimates:
{{
    "weight_lbs": "weight in pounds (decimal)",
    "length_inches": "package length",
    "width_inches": "package width",
    "height_inches": "package height",
    "package_type": "box/envelope/padded",
    "fragile": true/false,
    "reasoning": "explain the estimates"
}}

Base estimates on typical product dimensions and industry standards.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        logger.info(f"Shipping details estimated: {result.get('weight_lbs')}lbs")
        return result
    except Exception as e:
        logger.error(f"Shipping estimation failed: {e}")
        return {
            "weight_lbs": 2.0,
            "length_inches": 12.0,
            "width_inches": 10.0,
            "height_inches": 4.0,
            "package_type": "box",
            "fragile": False,
            "reasoning": "Default estimates"
        }


# ============================================================================
# SPECIALIZED AGENTS
# ============================================================================

def create_product_research_agent() -> Agent:
    """Agent specialized in gathering product information from web sources"""
    return Agent(
        name="Product Researcher",
        model="gpt-4o",
        instructions="""
You are a product research specialist. Your job is to gather comprehensive
product information from web sources.

When given a brand and model:
1. Search for official specifications
2. Find current market pricing
3. Identify product identifiers (UPC, EAN, MPN)
4. Extract key features and specifications
5. Find high-quality product images

Always verify information from multiple sources when possible.
Be factual and avoid speculation.
""",
        tools=[web_search_product, get_ebay_category, estimate_shipping_details]
    )


def create_pricing_agent() -> Agent:
    """Agent specialized in market pricing analysis"""
    return Agent(
        name="Pricing Specialist",
        model="gpt-4o",
        instructions="""
You are a pricing expert for resale markets, especially eBay.

Your responsibilities:
1. Analyze current market conditions
2. Apply condition-based depreciation
3. Consider brand value and demand
4. Recommend competitive pricing
5. Provide price ranges for flexibility

Always explain your pricing rationale.
Focus on quick sale vs. maximum profit tradeoffs.
""",
        tools=[analyze_market_pricing]
    )


def create_listing_writer_agent() -> Agent:
    """Agent specialized in creating compelling eBay listings"""
    return Agent(
        name="Listing Writer",
        model="gpt-4o",
        instructions="""
You are an expert eBay listing copywriter.

Your responsibilities:
1. Create SEO-optimized titles (80 chars max)
2. Write detailed, honest descriptions
3. Format using eBay-friendly HTML
4. Extract and format item specifics
5. Ensure compliance with eBay policies

Always be honest about condition.
Focus on benefits and features that buyers care about.
Use clear, professional language.
""",
        tools=[generate_product_description, extract_item_specifics]
    )


def create_coordinator_agent() -> Agent:
    """Main coordinator agent that orchestrates the enrichment workflow"""
    # Create specialized agents
    researcher = create_product_research_agent()
    pricer = create_pricing_agent()
    writer = create_listing_writer_agent()

    return Agent(
        name="Enrichment Coordinator",
        model="gpt-4o",
        instructions="""
You are the coordinator for product listing enrichment.

Your workflow:
1. Hand off to Product Researcher to gather product data
2. Hand off to Pricing Specialist to determine optimal pricing
3. Hand off to Listing Writer to create listing content
4. Compile all information into a complete product record

Ensure all critical fields are populated before completing.
If any agent fails, try to work with available data or request clarification.
""",
        handoffs=[researcher, pricer, writer]
    )


# ============================================================================
# MAIN ENRICHMENT SYSTEM
# ============================================================================

class AgentBasedEnricher:
    """AI Agent-based product enrichment system"""

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the enrichment system.

        Args:
            openai_api_key: OpenAI API key (or reads from env)
        """
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set")

        os.environ["OPENAI_API_KEY"] = self.api_key
        self.coordinator = create_coordinator_agent()

    def enrich_product(
        self,
        sku: str,
        brand: str,
        model: str,
        condition: str
    ) -> EnrichedProduct:
        """
        Enrich a single product using the AI agent workflow.

        Args:
            sku: Product SKU
            brand: Product brand
            model: Product model
            condition: Item condition

        Returns:
            EnrichedProduct with all gathered information
        """
        logger.info(f"Starting enrichment for {sku}: {brand} {model}")

        # Create enrichment request
        request = f"""
Please enrich this product listing with all missing details:

SKU: {sku}
Brand: {brand}
Model: {model}
Condition: {condition}

I need you to:
1. Research the product and gather specifications
2. Determine the best eBay category
3. Analyze pricing for the given condition
4. Generate a compelling listing title and description
5. Extract relevant item specifics
6. Estimate shipping details

Coordinate with your specialized agents and compile complete results.
"""

        try:
            # Run the agent workflow
            result = Runner.run_sync(
                starting_agent=self.coordinator,
                input=request,
                max_turns=20  # Allow multiple agent interactions
            )

            # Parse the result and create EnrichedProduct
            # Note: In practice, you'd extract structured data from result.final_output
            product = self._parse_agent_output(
                sku, brand, model, condition,
                result.final_output
            )

            logger.info(f"Enrichment complete for {sku}")
            return product

        except Exception as e:
            logger.error(f"Enrichment failed for {sku}: {e}")
            # Return minimal product data
            return EnrichedProduct(
                sku=sku,
                brand=brand,
                model=model,
                condition=condition,
                title=f"{brand} {model}",
                confidence_score=0.0
            )

    def _parse_agent_output(
        self,
        sku: str,
        brand: str,
        model: str,
        condition: str,
        output: str
    ) -> EnrichedProduct:
        """
        Parse agent output into structured EnrichedProduct.

        In a production system, you'd use structured outputs or parse
        the agent's response more carefully. This is a simplified version.
        """
        # This is a simplified parser - in practice, you'd use structured outputs
        # or more sophisticated parsing

        return EnrichedProduct(
            sku=sku,
            brand=brand,
            model=model,
            condition=condition,
            title=f"{brand} {model}",
            description=output[:500] if output else "",
            confidence_score=0.8
        )

    def enrich_csv(
        self,
        input_csv: str,
        output_csv: str,
        sku_col: str = "sku",
        brand_col: str = "brand",
        model_col: str = "model",
        condition_col: str = "condition"
    ) -> pd.DataFrame:
        """
        Enrich all products in a CSV file.

        Args:
            input_csv: Path to input CSV
            output_csv: Path to output CSV
            sku_col: Name of SKU column
            brand_col: Name of brand column
            model_col: Name of model column
            condition_col: Name of condition column

        Returns:
            DataFrame with enriched products
        """
        logger.info(f"Loading CSV: {input_csv}")
        df = pd.read_csv(input_csv)

        enriched_products = []

        for idx, row in df.iterrows():
            sku = str(row.get(sku_col, f"ROW_{idx}"))
            brand = str(row.get(brand_col, ""))
            model = str(row.get(model_col, ""))
            condition = str(row.get(condition_col, "good"))

            if not brand and not model:
                logger.warning(f"Skipping row {idx}: missing brand and model")
                continue

            # Enrich the product
            enriched = self.enrich_product(sku, brand, model, condition)
            enriched_products.append(asdict(enriched))

            logger.info(f"Progress: {idx + 1}/{len(df)}")

        # Create output DataFrame
        result_df = pd.DataFrame(enriched_products)
        result_df.to_csv(output_csv, index=False)

        logger.info(f"Enriched CSV saved: {output_csv}")
        return result_df


def main():
    """Example usage"""
    # Initialize the enricher
    enricher = AgentBasedEnricher()

    # Example: Enrich a single product
    product = enricher.enrich_product(
        sku="TEST-001",
        brand="Apple",
        model="iPad Air 5th Gen",
        condition="like new"
    )

    print("\nEnriched Product:")
    print(f"Title: {product.title}")
    print(f"Category: {product.category_name}")
    print(f"Suggested Price: ${product.suggested_price}")
    print(f"Confidence: {product.confidence_score}")

    # Example: Enrich CSV file
    # enricher.enrich_csv(
    #     input_csv="products.csv",
    #     output_csv="products_enriched.csv"
    # )


if __name__ == "__main__":
    main()
