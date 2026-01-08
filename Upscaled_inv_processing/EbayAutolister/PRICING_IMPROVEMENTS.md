# Automated Pricing System - Improvement Roadmap

## 🎯 Current Status

✅ **Working**:
- Tavily API integration for web search
- Condition-based pricing formula (0.92 * base - condition penalty)
- Retail price estimation from brand/model patterns
- Multiple price points (BIN, min offer, auto-accept/decline)
- SQLite caching (24-hour TTL)
- Full B2 batch pricing

⚠️ **Needs Fixing**:
- eBay Browse API authentication (OAuth 400 error)
- Tavily → OpenAI extraction not finding sold prices consistently
- Retail price estimates are pattern-based, not precise

---

## 🚀 Improvement Areas

### 1. **BETTER PRODUCT IDENTIFICATION** (High Impact)

#### Problem:
- Model numbers like "A2449", "1866" are internal codes, not consumer names
- Hard to search eBay with these codes
- Pattern matching for retail prices is imprecise

#### Solutions:

**A. Use UPC Codes** (Recommended)
```python
def lookup_product_by_upc(upc: str) -> dict:
    """
    Use UPC to get exact product info
    APIs: UPCitemdb, Barcode Lookup, Amazon Product API
    Returns: brand, full model name, MSRP, category
    """
```

**Benefits**:
- Your inventory already has UPC codes (column in B2 CSV)
- Exact product match → accurate retail prices
- Get full product names for better eBay searches

**Implementation**:
```python
# Add to .env
UPCITEMDB_API_KEY=your_key_here

# In market_research.py
if upc:
    product_info = lookup_upc(upc)
    search_query = f"{product_info['brand']} {product_info['title']} sold ebay"
else:
    # Fallback to model number
```

**UPC APIs** (pick one):
- UPCitemdb.com - Free tier: 100 requests/day
- Barcodelookup.com - $20/month for 500/day
- DataForSEO - Product database API

---

**B. Model Number → Product Name Mapping**
```python
def resolve_model_number(brand: str, model: str) -> str:
    """
    Convert internal model numbers to consumer names

    Examples:
    - Apple A2449 → MacBook Air M1 13" 2020
    - Microsoft 1866 → Surface Pro 7
    - Asus GA401I → ROG Zephyrus G14
    """
```

**Data sources**:
- EveryMac.com API (for Apple products)
- Microsoft part number database
- Manufacturer spec sheets (scrape or API)
- Build your own mapping database from successful lookups

---

### 2. **FIX EBAY BROWSE API** (Medium Impact)

#### Problem:
```
ERROR - eBay Browse API authentication failed: 400 Client Error
```

#### Root Cause:
The OAuth scope or credentials format is incorrect.

#### Fix Steps:

**Step 1: Verify Credentials**
```bash
# Check your .env file
EBAY_CLIENT_ID=ConnorOD-Upscaled-PRD-9d6e07ac2-6830ad3d
EBAY_CLIENT_SECRET=PRD-d6e07ac24eba-7b48-4b15-8194-34bf
EBAY_SANDBOX=false  # Must be false for production
```

**Step 2: Test OAuth Manually**
```bash
curl -X POST 'https://api.ebay.com/identity/v1/oauth2/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'Authorization: Basic BASE64(client_id:client_secret)' \
  -d 'grant_type=client_credentials' \
  -d 'scope=https://api.ebay.com/oauth/api_scope'
```

**Step 3: Update browse_api.py**

The issue might be the scope. Try:
```python
# In browse_api.py, line ~75
data = {
    'grant_type': 'client_credentials',
    'scope': 'https://api.ebay.com/oauth/api_scope'  # Simplified scope
}
```

**Benefits of fixing**:
- Real-time active listing prices
- Competitive intelligence
- 60-90% confidence scores instead of 30%

---

### 3. **IMPROVE TAVILY → OPENAI EXTRACTION** (High Impact)

#### Problem:
Tavily finds eBay pages with prices, but OpenAI extraction returns 0 listings.

#### Debug First:
```python
# Save Tavily raw results to see what we're getting
import json

search_results = tavily.search(...)
with open('tavily_debug.json', 'w') as f:
    json.dump(search_results, f, indent=2)

# Review the actual content being sent to OpenAI
```

#### Solutions:

**A. Improve OpenAI Prompt** (Quick Win)
```python
prompt = f"""
You are a data extraction expert. Extract eBay listing prices from these search results.

SEARCH RESULTS:
{context}

TASK:
Find ALL dollar amounts that represent product prices.
Look for patterns like:
- "$419.64"
- "sold for $299"
- "18 bids · $95.00"
- "Buy It Now: $549.99"

Extract each price you find. If a listing shows multiple prices (was $X, now $Y), use the lower price.

Return JSON:
{{
  "listings": [
    {{"title": "...", "price": 419.64, "sold_date": "2024-12-02", "condition": "Used", "url": "..."}}
  ]
}}

IMPORTANT:
- Extract EVERY price between $50-$5000
- Use the product title from the search result
- Use the URL from the search result
- If unsure about condition, use "Used"
"""
```

**B. Add Regex Fallback** (Already implemented in `_parse_results_basic`)
Enhance the basic parser:
```python
def _parse_results_basic(search_results):
    # Extract ALL dollar amounts
    price_pattern = r'\$(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)'

    for result in search_results:
        content = result['content'] + ' ' + result['title']

        # Find all prices
        prices = re.findall(price_pattern, content)
        prices = [float(p.replace(',', '')) for p in prices]

        # Filter to reasonable range
        valid_prices = [p for p in prices if 50 <= p <= 5000]

        if valid_prices:
            # Use median price from this result
            median_price = statistics.median(valid_prices)
            # Add to sold_listings...
```

**C. Use Tavily's Extract Feature**
```python
# Tavily can extract structured data
search_results = tavily.search(
    query=search_query,
    search_depth="advanced",
    include_answer=True,  # Let Tavily summarize
    max_results=10
)

# Use the 'answer' field which is AI-generated summary
tavily_answer = search_results.get('answer', '')
# This might include price ranges directly
```

---

### 4. **ADD REAL RETAIL PRICE DATA** (High Impact)

#### Current: Pattern-based estimation
#### Better: Real product databases

**Option A: Keepa / CamelCamelCamel (Amazon prices)**
```python
import requests

def get_amazon_price(product_name: str) -> float:
    # Use Keepa API to get Amazon current/historical prices
    # Amazon prices are good proxies for retail value
    response = requests.get(
        'https://api.keepa.com/product',
        params={'key': KEEPA_API_KEY, 'domain': 1, 'asin': asin}
    )
    return response.json()['current_price']
```

**Option B: PriceAPI / DataForSEO**
```python
# Get multi-retailer pricing
def get_retail_price(brand: str, model: str) -> dict:
    # Returns prices from Amazon, Best Buy, Walmart, etc.
    # Use the median as "retail price"
```

**Option C: Build Historical Database**
```python
# Each time you successfully price an item, save it
def cache_retail_price(brand: str, model: str, price: float):
    db.execute(
        "INSERT INTO retail_prices VALUES (?, ?, ?, ?)",
        (brand, model, price, datetime.now())
    )

# Over time, build your own database
# For recurring products, use cached retail prices
```

---

### 5. **ADVANCED PRICING STRATEGIES** (Medium Impact)

#### A. Demand-Based Pricing
```python
def calculate_demand_score(brand: str, model: str) -> float:
    """
    High demand = price higher
    Low demand = price lower to move inventory

    Factors:
    - Active listing count (fewer = higher demand)
    - Sold listing count (more = higher demand)
    - eBay category trends (API: getCategoryTrends)
    - Google Trends data
    """

    if sold_count > 50 and active_count < 10:
        demand_multiplier = 1.05  # High demand, price up 5%
    elif sold_count < 5 and active_count > 50:
        demand_multiplier = 0.90  # Low demand, price down 10%
    else:
        demand_multiplier = 1.0

    return base_price * demand_multiplier
```

#### B. Time-Based Repricing
```python
def auto_reprice(sku: str, days_listed: int, views: int, watchers: int):
    """
    Automatically adjust price if item isn't selling

    Rules:
    - Listed 7 days, < 10 views: reduce 5%
    - Listed 14 days, no watchers: reduce 10%
    - Listed 30 days: reduce 15% or run auction
    - High watchers but no sales: reduce 3%
    """

    if days_listed >= 30:
        new_price = current_price * 0.85
        update_ebay_listing(sku, new_price)
        send_notification(f"Repriced {sku}: ${new_price}")
```

#### C. Seasonal Adjustments
```python
SEASONAL_MULTIPLIERS = {
    'laptops': {
        'back_to_school': (7, 9, 1.10),  # July-Sept: +10%
        'black_friday': (11, 11, 1.15),   # November: +15%
        'post_christmas': (1, 2, 0.90)    # Jan-Feb: -10%
    },
    'gaming': {
        'holiday': (11, 12, 1.20),        # Nov-Dec: +20%
        'summer': (6, 8, 0.95)            # June-Aug: -5%
    }
}

def apply_seasonal_adjustment(price: float, category: str, month: int) -> float:
    for season, (start, end, multiplier) in SEASONAL_MULTIPLIERS.get(category, {}).items():
        if start <= month <= end:
            return price * multiplier
    return price
```

---

### 6. **PRICING ANALYTICS & LEARNING** (Long-term)

#### A. Track Performance
```python
class PricingAnalytics:
    def track_listing(self, sku, listing_price, sold_price, days_to_sell):
        """
        Track actual performance vs predicted pricing
        """
        db.execute("""
            INSERT INTO pricing_performance
            VALUES (?, ?, ?, ?, ?)
        """, (sku, listing_price, sold_price, days_to_sell, datetime.now()))

    def analyze_accuracy(self):
        """
        How close were our prices to actual sold prices?
        Which conditions/brands/categories are most accurate?
        """
        return db.execute("""
            SELECT
                brand,
                AVG(sold_price / listing_price) as accuracy_ratio,
                AVG(days_to_sell) as avg_days
            FROM pricing_performance
            GROUP BY brand
        """)

    def recommend_adjustments(self):
        """
        Based on historical data, suggest pricing formula tweaks

        If Apple products consistently sell for 95% of listing in < 7 days:
        → Increase base_multiplier from 0.92 to 0.95

        If Samsung products sit for 30+ days:
        → Decrease base_multiplier from 0.92 to 0.88
        """
```

#### B. A/B Testing
```python
def ab_test_pricing():
    """
    Test different pricing strategies

    Group A: 50 items priced at current formula
    Group B: 50 items priced 5% higher

    Track: sell-through rate, days to sell, profit
    """
```

---

### 7. **MULTI-MARKETPLACE INTELLIGENCE** (Advanced)

```python
def get_cross_platform_pricing(brand: str, model: str) -> dict:
    """
    Compare prices across platforms

    Sources:
    - eBay (current)
    - Mercari API
    - Facebook Marketplace (scrape)
    - OfferUp API
    - Poshmark (for specific categories)

    Strategy:
    - Price 2-5% below lowest competitor on other platforms
    - Capture cross-platform shoppers
    """

    prices = {
        'ebay': get_ebay_price(brand, model),
        'mercari': get_mercari_price(brand, model),
        'facebook': get_facebook_price(brand, model)
    }

    # Price just below cheapest competitor
    min_price = min(prices.values())
    recommended_price = min_price * 0.97

    return {
        'recommended': recommended_price,
        'competitor_prices': prices,
        'reasoning': f"Priced 3% below cheapest ({min_price})"
    }
```

---

### 8. **BETTER INTEGRATION WITH YOUR WORKFLOW** (Quick Win)

#### Current State:
Standalone pricing scripts → Manual CSV workflow

#### Improved:
```python
# Modify agent_enricher.py to use UPC lookups + Tavily automatically

def enrich_product(sku, brand, model, condition, upc=None):
    """
    Enhanced enrichment workflow:
    1. Lookup UPC → get full product name + retail price
    2. Use full name for better Tavily searches
    3. Get sold comps with higher success rate
    4. Calculate pricing with real data
    5. All happens automatically during enrichment
    """

    # Step 1: UPC lookup
    if upc:
        product_data = lookup_upc(upc)
        full_name = product_data['title']
        retail_price = product_data['msrp']
    else:
        full_name = f"{brand} {model}"
        retail_price = estimate_retail_price(brand, model)

    # Step 2: Get market data with better search
    pricing = get_pricing_recommendation(
        brand=brand,
        model=full_name,  # Use full name, not model number
        condition=condition,
        retail_price=retail_price
    )

    # Step 3: Return enriched product with pricing
    return EnrichedProduct(
        sku=sku,
        brand=brand,
        model=model,
        title=full_name,
        retail_price=retail_price,
        buy_it_now_price=pricing.buy_it_now_price,
        # ... all other fields
    )
```

---

## 🎯 RECOMMENDED PRIORITY ORDER

### Phase 1: Quick Wins (This Week)
1. ✅ **Fix eBay Browse API OAuth** (2 hours)
   - Test credentials manually
   - Update scope/format
   - Get active listing data working

2. ✅ **Add UPC Lookup** (4 hours)
   - Sign up for UPCitemdb free tier
   - Integrate into pricing workflow
   - Use UPC codes from your B2 CSV

3. ✅ **Improve OpenAI Extraction** (2 hours)
   - Better prompt engineering
   - Add debug logging to see what's being extracted

### Phase 2: Foundation (Next 2 Weeks)
4. ✅ **Build Model Number Mapping** (6 hours)
   - Create database of model → product name
   - Start with your B2 batch products
   - Populate as you process more inventory

5. ✅ **Add Retail Price API** (4 hours)
   - Integrate Keepa or alternative
   - Replace pattern matching with real data

6. ✅ **Analytics Dashboard** (8 hours)
   - Track pricing accuracy
   - Monitor sell-through rates
   - Identify pricing adjustments needed

### Phase 3: Advanced (Month 2)
7. ✅ **Demand-Based Pricing** (8 hours)
   - Analyze sold/active listing ratios
   - Dynamic pricing multipliers

8. ✅ **Automated Repricing** (12 hours)
   - Monitor listed items
   - Auto-adjust if not selling
   - Integration with eBay Inventory API

9. ✅ **Multi-Marketplace** (16 hours)
   - Add Mercari, Facebook pricing
   - Competitive intelligence

### Phase 4: Machine Learning (Month 3+)
10. ✅ **Predictive Pricing Model** (20+ hours)
    - Train on historical sales
    - Predict optimal price by category/season/condition
    - Continuous learning from results

---

## 💡 IMMEDIATE NEXT STEPS

**To improve your pricing TODAY:**

1. **Get UPC API Key**
   ```bash
   # Sign up at https://www.upcitemdb.com/
   # Add to .env:
   UPCITEMDB_API_KEY=your_key_here
   ```

2. **Fix eBay OAuth**
   - I can help debug this right now
   - Just need to test the credentials

3. **Run Pricing on Full B2**
   - You have 25 items priced
   - Want to process the remaining items?

**Which improvement would you like to tackle first?**

- 🔥 Fix eBay Browse API (gets you 60-90% confidence immediately)
- 📦 Add UPC lookup (most accurate product data)
- 🎯 Improve Tavily extraction (better sold comps)
- 📊 Build analytics (track what's working)
- 🚀 Something else?

Let me know and I'll implement it right now!
