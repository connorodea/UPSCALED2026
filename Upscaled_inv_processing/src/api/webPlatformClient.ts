/**
 * Web Platform API Client
 *
 * Allows the CLI to communicate with the cross-listing web platform.
 * Enables features like multi-marketplace listing from the command line.
 */

import axios, { AxiosInstance } from 'axios';
import type { Product } from '../types.js';

export interface CrossListRequest {
  productId?: string;
  sku: string;
  marketplaces: string[];
  priceOverrides?: Record<string, number>;
}

export interface CrossListResponse {
  success: boolean;
  jobId?: string;
  status?: string;
  marketplaces?: Record<string, { status: string }>;
  error?: string;
}

export interface MarketplaceStatus {
  marketplace: string;
  status: 'active' | 'pending' | 'error' | 'not_listed';
  externalId?: string;
  listingUrl?: string;
  price?: number;
  listedAt?: string;
}

export class WebPlatformClient {
  private client: AxiosInstance;
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:3002') {
    this.baseUrl = baseUrl;
    this.client = axios.create({
      baseURL: `${baseUrl}/api`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Check if web platform is running
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  /**
   * Cross-list a product to multiple marketplaces
   */
  async crossListProduct(request: CrossListRequest): Promise<CrossListResponse> {
    try {
      const response = await this.client.post('/products/cross-list', request);
      return response.data;
    } catch (error: any) {
      console.error('Cross-listing failed:', error.response?.data || error.message);
      return {
        success: false,
        error: error.response?.data?.error || error.message,
      };
    }
  }

  /**
   * Get marketplace listing status for a product
   */
  async getMarketplaceStatus(sku: string): Promise<MarketplaceStatus[]> {
    try {
      const response = await this.client.get(`/products/${sku}/marketplaces`);
      return response.data.listings || [];
    } catch (error: any) {
      console.error('Failed to get marketplace status:', error.message);
      return [];
    }
  }

  /**
   * Get all products from the web platform
   */
  async getProducts(filters?: {
    batchId?: string;
    grade?: string;
    marketplace?: string;
  }): Promise<any[]> {
    try {
      const response = await this.client.get('/products', { params: filters });
      return response.data.products || [];
    } catch (error: any) {
      console.error('Failed to fetch products:', error.message);
      return [];
    }
  }

  /**
   * Delist a product from a specific marketplace
   */
  async delistProduct(sku: string, marketplace: string): Promise<boolean> {
    try {
      const response = await this.client.post(`/products/${sku}/delist`, {
        marketplace,
      });
      return response.data.success;
    } catch (error: any) {
      console.error('Delisting failed:', error.message);
      return false;
    }
  }

  /**
   * Bulk cross-list multiple products
   */
  async bulkCrossListBatch(
    batchNumber: string,
    marketplaces: string[]
  ): Promise<CrossListResponse> {
    try {
      const response = await this.client.post('/products/bulk/cross-list', {
        batchNumber,
        marketplaces,
      });
      return response.data;
    } catch (error: any) {
      console.error('Bulk cross-listing failed:', error.message);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Get analytics for the dashboard
   */
  async getAnalytics(): Promise<any> {
    try {
      const response = await this.client.get('/analytics');
      return response.data;
    } catch (error: any) {
      console.error('Failed to fetch analytics:', error.message);
      return null;
    }
  }

  /**
   * Enrich product listing using AI
   */
  async enrichProductListing(product: {
    sku: string;
    manufacturer?: string;
    model?: string;
    condition: string;
    marketplace: string;
  }): Promise<{
    title?: string;
    description?: string;
    suggestedPrice?: number;
  }> {
    try {
      const response = await this.client.post('/ai/enrich', product);
      return response.data;
    } catch (error: any) {
      console.error('AI enrichment failed:', error.message);
      return {};
    }
  }
}

export default WebPlatformClient;
