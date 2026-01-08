/**
 * Prisma Database Adapter
 *
 * Replaces CSV storage with PostgreSQL via Prisma ORM.
 * Maintains backwards compatibility with existing CLI workflow.
 */

import { PrismaClient } from '@prisma/client';
import type { Product, Grade } from '../types.js';

export class PrismaAdapter {
  private prisma: PrismaClient;

  constructor() {
    // Connect to the shared database (same as web platform)
    this.prisma = new PrismaClient({
      log: process.env.NODE_ENV === 'development' ? ['error', 'warn'] : ['error'],
    });
  }

  /**
   * Initialize connection and ensure database is ready
   */
  async initialize(): Promise<void> {
    try {
      await this.prisma.$connect();
      console.log('✓ Connected to PostgreSQL database');
    } catch (error) {
      console.error('✗ Failed to connect to database:', error);
      throw error;
    }
  }

  /**
   * Save a product to the database
   * Replaces: csvStorage.save(product)
   */
  async saveProduct(product: Product): Promise<void> {
    try {
      await this.prisma.product.upsert({
        where: { sku: product.sku },
        update: {
          grade: product.grade,
          location: product.location,
          batchId: this.extractBatchNumber(product.batchId),
          warehouseTag: product.warehouseTag || null,
          upc: product.upc || null,
          manufacturer: product.manufacturer || null,
          model: product.model || null,
          notes: product.notes || null,
          updatedAt: new Date(),
        },
        create: {
          sku: product.sku,
          grade: product.grade,
          location: product.location,
          batchId: this.extractBatchNumber(product.batchId),
          warehouseTag: product.warehouseTag || null,
          upc: product.upc || null,
          manufacturer: product.manufacturer || null,
          model: product.model || null,
          notes: product.notes || null,
        },
      });
    } catch (error) {
      console.error('Failed to save product:', error);
      throw error;
    }
  }

  /**
   * Get all products from database
   * Replaces: csvStorage.loadAll()
   */
  async getAllProducts(): Promise<Product[]> {
    const products = await this.prisma.product.findMany({
      orderBy: { createdAt: 'desc' },
    });

    return products.map(p => this.dbProductToCliProduct(p));
  }

  /**
   * Get products by batch ID
   */
  async getProductsByBatch(batchNumber: string): Promise<Product[]> {
    const products = await this.prisma.product.findMany({
      where: { batchId: batchNumber },
      orderBy: { createdAt: 'asc' },
    });

    return products.map(p => this.dbProductToCliProduct(p));
  }

  /**
   * Update batch information
   */
  async updateBatch(batchNumber: string, data: {
    totalItems?: number;
    processedItems?: number;
    status?: 'active' | 'completed' | 'exported';
  }): Promise<void> {
    await this.prisma.batch.upsert({
      where: { batchNumber },
      update: {
        ...data,
        completedAt: data.status === 'completed' ? new Date() : undefined,
      },
      create: {
        batchNumber,
        location: 'DEN001', // Default location
        totalItems: data.totalItems || 0,
        processedItems: data.processedItems || 0,
        status: data.status || 'active',
      },
    });
  }

  /**
   * Get batch information
   */
  async getBatch(batchNumber: string) {
    return await this.prisma.batch.findUnique({
      where: { batchNumber },
      include: {
        products: {
          orderBy: { createdAt: 'asc' },
        },
      },
    });
  }

  /**
   * Get all batches
   */
  async getAllBatches() {
    return await this.prisma.batch.findMany({
      orderBy: { createdAt: 'desc' },
      include: {
        _count: {
          select: { products: true },
        },
      },
    });
  }

  /**
   * Check if a product exists in the marketplace
   */
  async isProductListed(sku: string, marketplace?: string): Promise<boolean> {
    const product = await this.prisma.product.findUnique({
      where: { sku },
      include: {
        marketplaceListings: marketplace
          ? { where: { marketplace, status: 'active' } }
          : { where: { status: 'active' } },
      },
    });

    return (product?.marketplaceListings.length || 0) > 0;
  }

  /**
   * Get marketplace listings for a product
   */
  async getMarketplaceListings(sku: string) {
    const product = await this.prisma.product.findUnique({
      where: { sku },
      include: {
        marketplaceListings: {
          orderBy: { createdAt: 'desc' },
        },
      },
    });

    return product?.marketplaceListings || [];
  }

  /**
   * Close database connection
   */
  async disconnect(): Promise<void> {
    await this.prisma.$disconnect();
  }

  // ============================================================
  // HELPER METHODS
  // ============================================================

  /**
   * Extract batch number from batchId (e.g., "B1UID001" → "B1")
   */
  private extractBatchNumber(batchId: string): string {
    const match = batchId.match(/^(B\d+)/);
    return match ? match[1] : 'B1';
  }

  /**
   * Convert database product to CLI product format
   */
  private dbProductToCliProduct(dbProduct: any): Product {
    return {
      sku: dbProduct.sku,
      grade: dbProduct.grade as Grade,
      location: dbProduct.location,
      batchId: dbProduct.batchId,
      warehouseTag: dbProduct.warehouseTag || undefined,
      upc: dbProduct.upc || undefined,
      manufacturer: dbProduct.manufacturer || undefined,
      model: dbProduct.model || undefined,
      notes: dbProduct.notes || undefined,
      timestamp: dbProduct.createdAt.toISOString(),
      manifestId: dbProduct.manifestId || undefined,
      palletId: dbProduct.palletId || undefined,
      unitId: dbProduct.unitId || undefined,
    };
  }
}

export default PrismaAdapter;
