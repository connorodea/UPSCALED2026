/**
 * Marketplace adapters registry
 *
 * Central export for all marketplace integrations
 */

export { MarketplaceAdapter } from './base/MarketplaceAdapter';
export * from './base/types';

// Marketplace adapters
export { EbayAdapter } from './ebay';

// TODO: Add more marketplace adapters
// export { PoshmarkAdapter } from './poshmark';
// export { MercariAdapter } from './mercari';
// export { ShopifyAdapter } from './shopify';
// export { DepopAdapter } from './depop';
// export { EtsyAdapter } from './etsy';
// export { GrailedAdapter } from './grailed';
// export { VintedAdapter } from './vinted';
// export { WhatnotAdapter } from './whatnot';
// export { FacebookMarketplaceAdapter } from './facebook';
