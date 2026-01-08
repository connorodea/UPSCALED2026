/**
 * Marketplace Integration
 *
 * Simple integration with the cross-listing web platform
 */

import axios, { AxiosInstance } from 'axios';
import type { Product } from './types.js';
import fs from 'fs/promises';
import path from 'path';

export interface MarketplaceStatus {
  marketplace: string;
  status: 'active' | 'pending' | 'error' | 'not_listed';
  externalId?: string;
  listingUrl?: string;
  price?: number;
  listedAt?: string;
}

export class MarketplaceIntegration {
  private client: AxiosInstance;
  private webPlatformUrl: string;
  private isAvailable: boolean;

  constructor() {
    this.webPlatformUrl = process.env.WEB_PLATFORM_URL || 'http://localhost:3002';
    this.isAvailable = false;

    this.client = axios.create({
      baseURL: `${this.webPlatformUrl}/api`,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Check if web platform is running
   */
  async checkAvailability(): Promise<boolean> {
    try {
      const response = await axios.get(this.webPlatformUrl, { timeout: 3000 });
      this.isAvailable = response.status === 200;
      return this.isAvailable;
    } catch (error) {
      this.isAvailable = false;
      return false;
    }
  }

  /**
   * Get marketplace status for a product SKU
   */
  async getMarketplaceStatus(sku: string): Promise<MarketplaceStatus[]> {
    if (!this.isAvailable) {
      throw new Error('Web platform is not running');
    }

    try {
      const response = await this.client.get(`/products/${sku}/marketplaces`);
      return response.data.listings || [];
    } catch (error: any) {
      if (error.response?.status === 404) {
        return []; // Product not found in web platform
      }
      throw new Error(`Failed to get marketplace status: ${error.message}`);
    }
  }

  /**
   * Cross-list a product to multiple marketplaces
   */
  async crossListProduct(params: {
    sku: string;
    marketplaces: string[];
    priceOverrides?: Record<string, number>;
  }): Promise<{
    success: boolean;
    jobId?: string;
    error?: string;
  }> {
    if (!this.isAvailable) {
      throw new Error('Web platform is not running. Start it with: cd ../upscaled-crosslist && npm run dev');
    }

    try {
      const response = await this.client.post('/products/cross-list', params);
      return {
        success: true,
        jobId: response.data.jobId,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || error.message,
      };
    }
  }

  /**
   * Get available marketplaces
   */
  getAvailableMarketplaces(): Array<{ name: string; value: string }> {
    return [
      { name: 'eBay', value: 'ebay' },
      { name: 'Poshmark', value: 'poshmark' },
      { name: 'Mercari', value: 'mercari' },
      { name: 'Shopify', value: 'shopify' },
      { name: 'Depop', value: 'depop' },
      { name: 'Facebook Marketplace', value: 'facebook' },
      { name: 'Etsy', value: 'etsy' },
      { name: 'Grailed', value: 'grailed' },
      { name: 'Vinted', value: 'vinted' },
      { name: 'Whatnot', value: 'whatnot' },
    ];
  }

  /**
   * Check if web platform is available
   */
  isWebPlatformAvailable(): boolean {
    return this.isAvailable;
  }

  /**
   * Get web platform URL
   */
  getWebPlatformUrl(): string {
    return this.webPlatformUrl;
  }

  /**
   * Get available batch files
   */
  async getAvailableBatches(): Promise<string[]> {
    const dataDir = path.join(process.cwd(), 'data');
    try {
      const files = await fs.readdir(dataDir);
      const batchFiles = files
        .filter(f => /^B\d+\.csv$/.test(f))
        .sort((a, b) => {
          const numA = parseInt(a.match(/\d+/)?.[0] || '0');
          const numB = parseInt(b.match(/\d+/)?.[0] || '0');
          return numA - numB;
        });
      return batchFiles;
    } catch (error) {
      return [];
    }
  }

  /**
   * Read batch CSV and extract SKUs
   */
  async readBatchSKUs(batchFile: string): Promise<string[]> {
    const filePath = path.join(process.cwd(), 'data', batchFile);
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      const lines = content.split(/\r?\n/).filter(line => line.trim() !== '');

      // Skip header if present, extract SKU (first column)
      const skus = lines
        .filter(line => !line.startsWith('SKU,')) // Skip header
        .map(line => {
          const firstComma = line.indexOf(',');
          if (firstComma === -1) return line.trim();
          return line.substring(0, firstComma).trim();
        })
        .filter(sku => sku && sku !== 'SKU');

      // Remove duplicates
      return [...new Set(skus)];
    } catch (error: any) {
      throw new Error(`Failed to read batch file: ${error.message}`);
    }
  }

  /**
   * Cross-list an entire batch to multiple marketplaces
   */
  async crossListBatch(params: {
    batchFile: string;
    marketplaces: string[];
    priceOverrides?: Record<string, number>;
  }): Promise<{
    success: boolean;
    totalProducts: number;
    jobId?: string;
    error?: string;
  }> {
    if (!this.isAvailable) {
      throw new Error('Web platform is not running. Start it with: cd ../upscaled-crosslist && npm run dev');
    }

    try {
      // Read all SKUs from batch file
      const skus = await this.readBatchSKUs(params.batchFile);

      if (skus.length === 0) {
        return {
          success: false,
          totalProducts: 0,
          error: 'No products found in batch file'
        };
      }

      // Send bulk cross-list request
      const response = await this.client.post('/products/cross-list/batch', {
        skus,
        marketplaces: params.marketplaces,
        priceOverrides: params.priceOverrides
      });

      return {
        success: true,
        totalProducts: skus.length,
        jobId: response.data.jobId
      };
    } catch (error: any) {
      return {
        success: false,
        totalProducts: 0,
        error: error.response?.data?.error || error.message
      };
    }
  }
}
