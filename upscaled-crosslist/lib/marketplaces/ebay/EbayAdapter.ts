/**
 * eBay Marketplace Adapter
 *
 * Extends the existing Upscaled eBay integration to work with the new
 * marketplace adapter pattern.
 *
 * This adapter integrates with the Python EbayAutolister service for
 * AI-powered listing enrichment and eBay API operations.
 */

import { MarketplaceAdapter } from '../base/MarketplaceAdapter';
import type {
  ListingParams,
  ListingResult,
  UpdateListingParams,
  SoldItem,
  MarketplaceCredentials,
} from '../base/types';
import {
  EBAY_DEFAULTS,
  GRADE_TO_EBAY_CONDITION,
  GRADE_PRICE_MULTIPLIER,
  BRAND_BASE_PRICES,
  type EbayCredentials,
} from './config';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';

const execAsync = promisify(exec);

export class EbayAdapter extends MarketplaceAdapter {
  readonly marketplace = 'ebay';
  private pythonServicePath: string;

  constructor(credentials: EbayCredentials) {
    super(credentials);

    // Path to Python EbayAutolister service
    this.pythonServicePath = path.join(
      process.cwd(),
      '..',
      'Upscaled_inv_processing',
      'EbayAutolister'
    );
  }

  /**
   * Authenticate with eBay API
   */
  async authenticate(): Promise<boolean> {
    try {
      const ebayCredentials = this.credentials as EbayCredentials;

      // Verify all required credentials are present
      if (
        !ebayCredentials.appId ||
        !ebayCredentials.certId ||
        !ebayCredentials.devId ||
        !ebayCredentials.authToken
      ) {
        console.error('Missing eBay API credentials');
        return false;
      }

      // Test authentication by making a simple API call
      // TODO: Implement actual eBay API health check
      // For now, just verify credentials exist
      return true;
    } catch (error) {
      console.error('eBay authentication failed:', error);
      return false;
    }
  }

  /**
   * Create a listing on eBay
   */
  async createListing(params: ListingParams): Promise<ListingResult> {
    try {
      this.validateListingParams(params);

      // Transform product data to eBay CSV format
      const ebayCSVLine = this.transformToEbayFormat(params);

      // Create temporary CSV file for Python service
      const tempCSVPath = path.join('/tmp', `ebay_listing_${params.sku}.csv`);
      const ebayHeader = 'sku,title,description,condition,category_id,price,quantity,brand,mpn,weight,dimensions,images';
      await fs.writeFile(tempCSVPath, `${ebayHeader}\n${ebayCSVLine}`);

      // Call Python EbayAutolister to create listing
      const command = `cd ${this.pythonServicePath} && python3 cli.py process "${tempCSVPath}" --create-offers`;

      const { stdout, stderr } = await execAsync(command, {
        env: {
          ...process.env,
          EBAY_APP_ID: (this.credentials as EbayCredentials).appId,
          EBAY_CERT_ID: (this.credentials as EbayCredentials).certId,
          EBAY_DEV_ID: (this.credentials as EbayCredentials).devId,
          EBAY_AUTH_TOKEN: (this.credentials as EbayCredentials).authToken,
        },
      });

      if (stderr && !stderr.includes('WARNING')) {
        console.error('eBay listing error:', stderr);
      }

      // Parse output for eBay item ID
      // The Python service should return the item ID in its output
      const itemIdMatch = stdout.match(/Item ID: (\d+)/);
      const externalId = itemIdMatch ? itemIdMatch[1] : undefined;

      // Clean up temp file
      await fs.unlink(tempCSVPath).catch(() => {});

      return {
        success: true,
        externalId,
        listingUrl: externalId
          ? `https://www.ebay.com/itm/${externalId}`
          : undefined,
        marketplaceData: { stdout, stderr },
      };
    } catch (error: any) {
      console.error('eBay listing creation failed:', error);
      return {
        success: false,
        error: error.message || 'Unknown error',
      };
    }
  }

  /**
   * Update an existing eBay listing
   */
  async updateListing(
    externalId: string,
    params: UpdateListingParams
  ): Promise<ListingResult> {
    try {
      // TODO: Implement eBay listing update via API
      // For now, return not implemented
      console.warn('eBay update listing not yet implemented');

      return {
        success: false,
        error: 'Update listing not yet implemented for eBay',
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Unknown error',
      };
    }
  }

  /**
   * Delete/end an eBay listing
   */
  async deleteListing(externalId: string): Promise<boolean> {
    try {
      // TODO: Implement eBay EndItem API call
      console.warn('eBay delete listing not yet implemented');
      return false;
    } catch (error) {
      console.error('eBay delete listing failed:', error);
      return false;
    }
  }

  /**
   * Get eBay listing details
   */
  async getListing(externalId: string): Promise<any> {
    try {
      // TODO: Implement eBay GetItem API call
      console.warn('eBay get listing not yet implemented');
      return null;
    } catch (error) {
      console.error('eBay get listing failed:', error);
      return null;
    }
  }

  /**
   * Detect sold items on eBay (for auto-delist)
   */
  async detectSoldItems(): Promise<SoldItem[]> {
    try {
      // TODO: Implement eBay GetOrders or GetSellerTransactions API call
      // to fetch recent sales
      console.warn('eBay sold items detection not yet implemented');
      return [];
    } catch (error) {
      console.error('eBay sold items detection failed:', error);
      return [];
    }
  }

  // ===================================================================
  // HELPER METHODS
  // ===================================================================

  /**
   * Transform product data to eBay CSV format
   * Preserves existing format from Upscaled_inv_processing
   */
  private transformToEbayFormat(params: ListingParams): string {
    const brand = params.brand || 'Generic';
    const mpn = params.model || params.sku;
    const condition = GRADE_TO_EBAY_CONDITION[params.condition] || 'USED_GOOD';

    // Calculate price using grade multiplier
    const basePrice =
      BRAND_BASE_PRICES[brand] || BRAND_BASE_PRICES['default'];
    const multiplier = GRADE_PRICE_MULTIPLIER[params.condition] || 0.70;
    const price = (basePrice * multiplier).toFixed(2);

    // Use provided price if available, otherwise use calculated price
    const finalPrice = params.price || parseFloat(price);

    // Create title (max 80 chars for eBay)
    const title = params.title
      ? params.title.substring(0, 80)
      : `${brand} ${params.model || 'Product'} - ${params.condition} - ${params.sku}`.substring(0, 80);

    // Create description
    const description = params.description || [
      `${brand} ${params.model || 'Product'}`,
      `Condition: ${params.condition}`,
      `SKU: ${params.sku}`,
      params.upc ? `UPC: ${params.upc}` : '',
    ].filter(Boolean).join(' | ');

    // Build eBay CSV line
    return [
      params.sku,
      `"${title}"`,
      `"${description}"`,
      condition,
      EBAY_DEFAULTS.categoryId,
      finalPrice.toFixed(2),
      params.quantity || EBAY_DEFAULTS.quantity,
      `"${brand}"`,
      `"${mpn}"`,
      params.weightLbs || EBAY_DEFAULTS.weightLbs,
      `"${EBAY_DEFAULTS.dimensions}"`,
      params.images.length > 0 ? `"${params.images.join(',')}"` : '""',
    ].join(',');
  }

  /**
   * Bulk create listings on eBay
   * Optimized for batch processing (existing workflow)
   */
  async bulkCreate(listings: ListingParams[]): Promise<ListingResult[]> {
    try {
      // Transform all listings to eBay CSV format
      const ebayHeader = 'sku,title,description,condition,category_id,price,quantity,brand,mpn,weight,dimensions,images';
      const ebayLines = listings.map(listing => this.transformToEbayFormat(listing));
      const csvContent = [ebayHeader, ...ebayLines].join('\n');

      // Create temporary batch CSV file
      const timestamp = Date.now();
      const tempCSVPath = path.join('/tmp', `ebay_batch_${timestamp}.csv`);
      await fs.writeFile(tempCSVPath, csvContent);

      // Call Python EbayAutolister for batch processing
      const command = `cd ${this.pythonServicePath} && python3 cli.py process "${tempCSVPath}" --create-offers`;

      const { stdout, stderr } = await execAsync(command, {
        env: {
          ...process.env,
          EBAY_APP_ID: (this.credentials as EbayCredentials).appId,
          EBAY_CERT_ID: (this.credentials as EbayCredentials).certId,
          EBAY_DEV_ID: (this.credentials as EbayCredentials).devId,
          EBAY_AUTH_TOKEN: (this.credentials as EbayCredentials).authToken,
        },
      });

      console.log('eBay batch listing output:', stdout);

      if (stderr && !stderr.includes('WARNING')) {
        console.error('eBay batch listing errors:', stderr);
      }

      // Clean up temp file
      await fs.unlink(tempCSVPath).catch(() => {});

      // Return success for all listings (Python service handles individual errors)
      return listings.map(listing => ({
        success: true,
        marketplaceData: { stdout, stderr },
      }));
    } catch (error: any) {
      console.error('eBay bulk create failed:', error);

      // Return error for all listings
      return listings.map(() => ({
        success: false,
        error: error.message || 'Bulk create failed',
      }));
    }
  }

  /**
   * Suggest optimal price for eBay
   * Uses grade multiplier system
   */
  async suggestPrice(params: ListingParams): Promise<number> {
    const brand = params.brand || 'Generic';
    const basePrice = BRAND_BASE_PRICES[brand] || BRAND_BASE_PRICES['default'];
    const multiplier = GRADE_PRICE_MULTIPLIER[params.condition] || 0.70;

    return Math.round(basePrice * multiplier * 100) / 100;
  }

  /**
   * Format condition for eBay
   */
  protected formatCondition(grade: string): string {
    return GRADE_TO_EBAY_CONDITION[grade] || 'USED_GOOD';
  }
}

export default EbayAdapter;
