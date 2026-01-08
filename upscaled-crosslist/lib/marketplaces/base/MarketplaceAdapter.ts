/**
 * Abstract base class for marketplace integrations
 *
 * All marketplace adapters (eBay, Poshmark, Mercari, etc.) must extend this class
 * and implement the core methods.
 *
 * This provides a unified interface for cross-listing operations.
 */

import type {
  ListingParams,
  ListingResult,
  UpdateListingParams,
  SoldItem,
  MarketplaceCredentials,
  MarketplaceStats,
} from './types';

export abstract class MarketplaceAdapter {
  // Marketplace identifier (e.g., 'ebay', 'poshmark', 'mercari')
  abstract readonly marketplace: string;

  // API credentials
  protected credentials: MarketplaceCredentials;

  constructor(credentials: MarketplaceCredentials) {
    this.credentials = credentials;
  }

  // ===================================================================
  // CORE OPERATIONS (must be implemented by all adapters)
  // ===================================================================

  /**
   * Authenticate with the marketplace API
   * @returns true if authentication successful
   */
  abstract authenticate(): Promise<boolean>;

  /**
   * Create a new listing on the marketplace
   * @param params - Product and listing details
   * @returns Result with external ID and URL if successful
   */
  abstract createListing(params: ListingParams): Promise<ListingResult>;

  /**
   * Update an existing listing
   * @param externalId - Marketplace's listing ID
   * @param params - Fields to update
   * @returns Result indicating success/failure
   */
  abstract updateListing(
    externalId: string,
    params: UpdateListingParams
  ): Promise<ListingResult>;

  /**
   * Delete/end a listing
   * @param externalId - Marketplace's listing ID
   * @returns true if successfully deleted
   */
  abstract deleteListing(externalId: string): Promise<boolean>;

  /**
   * Get listing details
   * @param externalId - Marketplace's listing ID
   * @returns Listing data
   */
  abstract getListing(externalId: string): Promise<any>;

  /**
   * Detect items that have sold (for auto-delist)
   * @returns Array of sold item IDs
   */
  abstract detectSoldItems(): Promise<SoldItem[]>;

  // ===================================================================
  // OPTIONAL OPERATIONS (can be overridden for marketplace-specific logic)
  // ===================================================================

  /**
   * Sync inventory from marketplace
   * Fetches all active listings and syncs to local database
   */
  async syncInventory(): Promise<void> {
    // Default implementation: no-op
    // Override for marketplaces that support bulk inventory fetching
  }

  /**
   * Bulk create listings
   * Default: sequential creation
   * Override for marketplaces with bulk upload APIs
   */
  async bulkCreate(listings: ListingParams[]): Promise<ListingResult[]> {
    const results: ListingResult[] = [];

    for (const listing of listings) {
      try {
        const result = await this.createListing(listing);
        results.push(result);
      } catch (error: any) {
        results.push({
          success: false,
          error: error.message || 'Unknown error',
        });
      }
    }

    return results;
  }

  /**
   * Bulk update listings
   * Default: sequential updates
   */
  async bulkUpdate(
    updates: Array<{ externalId: string; params: UpdateListingParams }>
  ): Promise<ListingResult[]> {
    const results: ListingResult[] = [];

    for (const { externalId, params } of updates) {
      try {
        const result = await this.updateListing(externalId, params);
        results.push(result);
      } catch (error: any) {
        results.push({
          success: false,
          error: error.message || 'Unknown error',
        });
      }
    }

    return results;
  }

  /**
   * Suggest optimal price for a product
   * Default: return provided price
   * Override to implement marketplace-specific pricing logic
   */
  async suggestPrice(params: ListingParams): Promise<number> {
    return params.price;
  }

  /**
   * Get marketplace statistics
   * Default: basic stats
   * Override for marketplace-specific analytics
   */
  async getStats(): Promise<MarketplaceStats> {
    return {
      activeListings: 0,
      soldToday: 0,
      totalRevenue: 0,
      averagePrice: 0,
    };
  }

  /**
   * Relist an item (for boosting visibility)
   * Default: delete + recreate
   * Override for marketplaces with native relist features
   */
  async relistItem(externalId: string, params: ListingParams): Promise<ListingResult> {
    // Delete old listing
    await this.deleteListing(externalId);

    // Create new listing
    return await this.createListing(params);
  }

  // ===================================================================
  // UTILITY METHODS
  // ===================================================================

  /**
   * Format condition/grade for marketplace
   * Override for marketplace-specific condition formats
   */
  protected formatCondition(grade: string): string {
    const conditionMap: Record<string, string> = {
      'LN': 'Like New',
      'VG': 'Very Good',
      'G': 'Good',
      'AC': 'Acceptable',
      'SA': 'For Parts',
    };

    return conditionMap[grade] || grade;
  }

  /**
   * Calculate price based on grade multiplier
   */
  protected calculateGradePrice(basePrice: number, grade: string): number {
    const multipliers: Record<string, number> = {
      'LN': 1.0,
      'VG': 0.85,
      'G': 0.70,
      'AC': 0.55,
      'SA': 0.30,
    };

    const multiplier = multipliers[grade] || 0.70;
    return Math.round(basePrice * multiplier * 100) / 100;
  }

  /**
   * Validate listing parameters
   * Override for marketplace-specific validation
   */
  protected validateListingParams(params: ListingParams): void {
    if (!params.title || params.title.length === 0) {
      throw new Error('Title is required');
    }

    if (!params.price || params.price <= 0) {
      throw new Error('Price must be greater than 0');
    }

    if (!params.sku) {
      throw new Error('SKU is required');
    }
  }

  /**
   * Rate limiting helper
   * Override to implement marketplace-specific rate limits
   */
  protected async rateLimit(): Promise<void> {
    // Default: no rate limiting
    // Override to add delays between API calls
  }
}

export default MarketplaceAdapter;
