/**
 * eBay-specific configuration
 * Ported from Upscaled_inv_processing/src/ebayConfig.ts
 */

export interface EbayCredentials {
  appId: string;
  certId: string;
  devId: string;
  authToken: string;
  environment: 'SANDBOX' | 'PRODUCTION';
}

export interface EbayListingDefaults {
  categoryId: string;
  quantity: number;
  weightLbs: number;
  dimensions: string;
  shippingService?: string;
  returnPolicy?: string;
  paymentPolicy?: string;
}

// Default eBay listing settings
export const EBAY_DEFAULTS: EbayListingDefaults = {
  categoryId: '58058', // Consumer Electronics
  quantity: 1,
  weightLbs: 1.0,
  dimensions: '6x4x2',
  shippingService: 'USPS_PRIORITY',
  returnPolicy: '30_DAYS',
  paymentPolicy: 'IMMEDIATE_PAYMENT',
};

// Grade to eBay condition mapping
export const GRADE_TO_EBAY_CONDITION: Record<string, string> = {
  'LN': 'LIKE_NEW',
  'VG': 'VERY_GOOD',
  'G': 'GOOD',
  'AC': 'ACCEPTABLE',
  'SA': 'FOR_PARTS_OR_NOT_WORKING',
};

// Grade to price multiplier (preserves existing pricing logic)
export const GRADE_PRICE_MULTIPLIER: Record<string, number> = {
  'LN': 1.0,
  'VG': 0.85,
  'G': 0.70,
  'AC': 0.55,
  'SA': 0.30,
};

// Base prices by brand (update as needed)
export const BRAND_BASE_PRICES: Record<string, number> = {
  'Samsung': 100.00,
  'Apple': 200.00,
  'Google': 150.00,
  'Microsoft': 120.00,
  'Sony': 110.00,
  'default': 50.00,
};

// eBay API endpoints
export const EBAY_API_ENDPOINTS = {
  sandbox: {
    trading: 'https://api.sandbox.ebay.com/ws/api.dll',
    finding: 'https://svcs.sandbox.ebay.com/services/search/FindingService/v1',
    shopping: 'https://open.api.sandbox.ebay.com/shopping',
  },
  production: {
    trading: 'https://api.ebay.com/ws/api.dll',
    finding: 'https://svcs.ebay.com/services/search/FindingService/v1',
    shopping: 'https://open.api.ebay.com/shopping',
  },
};
