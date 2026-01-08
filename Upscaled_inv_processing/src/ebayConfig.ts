// eBay listing configuration
export interface EbayListingDefaults {
  categoryId: string;
  quantity: number;
  weightLbs: number;
  dimensions: string;
  imagesUrl?: string;
}

// Default eBay listing settings
export const EBAY_DEFAULTS: EbayListingDefaults = {
  categoryId: '58058', // Electronics category - update as needed
  quantity: 1,
  weightLbs: 1.0,
  dimensions: '6x4x2',
  imagesUrl: undefined // Will use product-specific images if available
};

// Grade to condition mapping
export const GRADE_TO_CONDITION: Record<string, string> = {
  'LN': 'LIKE_NEW',
  'VG': 'VERY_GOOD',
  'G': 'GOOD',
  'AC': 'ACCEPTABLE',
  'SA': 'FOR_PARTS_OR_NOT_WORKING'
};

// Grade to price multiplier (base price will be determined per product type)
export const GRADE_PRICE_MULTIPLIER: Record<string, number> = {
  'LN': 1.0,
  'VG': 0.85,
  'G': 0.70,
  'AC': 0.55,
  'SA': 0.30
};
