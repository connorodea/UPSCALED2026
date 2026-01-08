/**
 * Common types for marketplace integrations
 */

export interface ListingParams {
  // Product identification
  sku: string;

  // Listing content
  title: string;
  description: string;

  // Pricing and inventory
  price: number;
  quantity: number;

  // Product details
  condition: string;  // Grade: LN, VG, G, AC, SA
  brand?: string;
  model?: string;
  upc?: string;

  // Physical attributes
  weightLbs?: number;
  dimensions?: {
    length: number;
    width: number;
    height: number;
  };

  // Media
  images: string[];  // URLs or local file paths

  // Category
  categoryId?: string;

  // Additional marketplace-specific data
  metadata?: Record<string, any>;
}

export interface ListingResult {
  success: boolean;
  externalId?: string;      // Marketplace's listing ID
  listingUrl?: string;       // Public URL to view the listing
  error?: string;            // Error message if failed
  marketplaceData?: any;     // Raw response from marketplace
}

export interface UpdateListingParams {
  title?: string;
  description?: string;
  price?: number;
  quantity?: number;
  images?: string[];
  status?: 'active' | 'paused' | 'ended';
}

export interface SoldItem {
  externalId: string;       // Marketplace listing ID
  soldAt: Date;
  soldPrice: number;
  buyerInfo?: {
    username?: string;
    email?: string;
  };
}

export interface MarketplaceCredentials {
  apiKey?: string;
  apiSecret?: string;
  authToken?: string;
  environment?: 'sandbox' | 'production';
  [key: string]: any;        // Allow marketplace-specific fields
}

export interface MarketplaceStats {
  activeListings: number;
  soldToday: number;
  totalRevenue: number;
  averagePrice: number;
}
