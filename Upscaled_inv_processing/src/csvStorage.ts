import { createObjectCsvWriter } from 'csv-writer';
import fs from 'fs/promises';
import path from 'path';
import { Product } from './types.js';

const CSV_FILE = path.join(process.cwd(), 'data', 'inventory.csv');

export class CSVStorage {
  private csvWriter;
  private dbEnabled: boolean;
  private db: any; // PrismaClient - loaded dynamically to avoid breaking existing installs

  constructor() {
    this.csvWriter = createObjectCsvWriter({
      path: CSV_FILE,
      header: [
        { id: 'sku', title: 'SKU' },
        { id: 'grade', title: 'Grade' },
        { id: 'location', title: 'Location' },
        { id: 'batchId', title: 'Batch ID' },
        { id: 'warehouseTag', title: 'Warehouse Tag' },
        { id: 'upc', title: 'UPC' },
        { id: 'manufacturer', title: 'Manufacturer' },
        { id: 'model', title: 'Model' },
        { id: 'notes', title: 'Notes' },
        { id: 'timestamp', title: 'Timestamp' },
        { id: 'manifestId', title: 'Manifest ID' },
        { id: 'palletId', title: 'Pallet ID' },
        { id: 'unitId', title: 'Unit ID' },
        { id: 'pidUid', title: 'PID-UID' }
      ],
      append: true
    });

    // Check if database mode is enabled
    this.dbEnabled = process.env.USE_DATABASE === 'true';
    this.db = null;
  }

  /**
   * Initialize database connection (called only if USE_DATABASE=true)
   */
  async initializeDatabase(): Promise<boolean> {
    if (!this.dbEnabled) {
      return false;
    }

    try {
      // Dynamically import Prisma to avoid breaking existing installs
      const { PrismaClient } = await import('@prisma/client');
      this.db = new PrismaClient({
        log: process.env.NODE_ENV === 'development' ? ['error'] : ['error'],
      });
      await this.db.$connect();
      return true;
    } catch (error) {
      console.warn('Database connection failed, falling back to CSV-only mode');
      this.dbEnabled = false;
      this.db = null;
      return false;
    }
  }

  /**
   * Save product to CSV (and optionally to database)
   */
  async saveProduct(product: Product): Promise<void> {
    const record = {
      sku: product.sku,
      grade: product.grade,
      location: product.location,
      batchId: product.batchId,
      warehouseTag: product.warehouseTag || '',
      upc: product.upc || '',
      manufacturer: product.manufacturer || '',
      model: product.model || '',
      notes: product.notes || '',
      timestamp: product.timestamp.toISOString(),
      manifestId: product.manifestId || '',
      palletId: product.palletId || '',
      unitId: product.unitId || '',
      pidUid: product.pidUid || ''
    };

    // Always write to CSV (preserves existing behavior)
    await this.csvWriter.writeRecords([record]);

    // Optionally write to database (dual-write mode)
    if (this.dbEnabled && this.db) {
      try {
        await this.saveToDatabase(product);
      } catch (error) {
        // Log error but don't fail - CSV is source of truth
        console.warn('Database write failed (CSV saved successfully):', error);
      }
    }
  }

  /**
   * Save product to PostgreSQL database
   */
  private async saveToDatabase(product: Product): Promise<void> {
    if (!this.db) return;

    const batchNumber = this.extractBatchNumber(product.batchId);

    await this.db.product.upsert({
      where: { sku: product.sku },
      update: {
        grade: product.grade,
        location: product.location,
        batchId: batchNumber,
        warehouseTag: product.warehouseTag || null,
        upc: product.upc || null,
        manufacturer: product.manufacturer || null,
        model: product.model || null,
        notes: product.notes || null,
        manifestId: product.manifestId || null,
        palletId: product.palletId || null,
        unitId: product.unitId || null,
        pidUid: product.pidUid || null,
        updatedAt: new Date(),
      },
      create: {
        sku: product.sku,
        grade: product.grade,
        location: product.location,
        batchId: batchNumber,
        warehouseTag: product.warehouseTag || null,
        upc: product.upc || null,
        manufacturer: product.manufacturer || null,
        model: product.model || null,
        notes: product.notes || null,
        manifestId: product.manifestId || null,
        palletId: product.palletId || null,
        unitId: product.unitId || null,
        pidUid: product.pidUid || null,
        createdAt: product.timestamp,
      },
    });
  }

  /**
   * Extract batch number from batchId (e.g., "B1UID001" → "B1")
   */
  private extractBatchNumber(batchId: string): string {
    const match = batchId.match(/^(B\d+)/);
    return match ? match[1] : 'B1';
  }

  private extractSku(line: string): string {
    if (!line) {
      return '';
    }

    if (line.startsWith('"')) {
      let field = '';
      for (let i = 1; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          if (line[i + 1] === '"') {
            field += '"';
            i++;
            continue;
          }
          break;
        }
        field += char;
      }
      return field;
    }

    const commaIndex = line.indexOf(',');
    if (commaIndex === -1) {
      return line;
    }
    return line.slice(0, commaIndex);
  }

  async deleteProductBySku(sku: string): Promise<number> {
    let data = '';
    try {
      data = await fs.readFile(CSV_FILE, 'utf-8');
    } catch (error: any) {
      if (error?.code === 'ENOENT') {
        return 0;
      }
      throw error;
    }

    const lines = data.split(/\r?\n/).filter(line => line.trim() !== '');
    const remaining: string[] = [];
    let deletedCount = 0;

    for (const line of lines) {
      if (this.extractSku(line) === sku) {
        deletedCount++;
      } else {
        remaining.push(line);
      }
    }

    if (deletedCount > 0) {
      await fs.mkdir(path.dirname(CSV_FILE), { recursive: true });
      const output = remaining.length > 0 ? `${remaining.join('\n')}\n` : '';
      await fs.writeFile(CSV_FILE, output);

      // Also delete from database if enabled
      if (this.dbEnabled && this.db) {
        try {
          await this.db.product.deleteMany({
            where: { sku: sku }
          });
        } catch (error) {
          console.warn('Database delete failed (CSV deleted successfully)');
        }
      }
    }

    return deletedCount;
  }

  async getLastSku(): Promise<string | null> {
    let data = '';
    try {
      data = await fs.readFile(CSV_FILE, 'utf-8');
    } catch (error: any) {
      if (error?.code === 'ENOENT') {
        return null;
      }
      throw error;
    }

    const lines = data.split(/\r?\n/).filter(line => line.trim() !== '');
    if (lines.length === 0) {
      return null;
    }

    return this.extractSku(lines[lines.length - 1]) || null;
  }

  async deleteLastProduct(): Promise<{
    deleted: boolean;
    sku: string | null;
    remainingLastSku: string | null;
  }> {
    let data = '';
    try {
      data = await fs.readFile(CSV_FILE, 'utf-8');
    } catch (error: any) {
      if (error?.code === 'ENOENT') {
        return { deleted: false, sku: null, remainingLastSku: null };
      }
      throw error;
    }

    const lines = data.split(/\r?\n/).filter(line => line.trim() !== '');
    if (lines.length === 0) {
      return { deleted: false, sku: null, remainingLastSku: null };
    }

    const deletedLine = lines.pop() as string;
    const deletedSku = this.extractSku(deletedLine) || null;
    const remainingLastSku = lines.length > 0 ? (this.extractSku(lines[lines.length - 1]) || null) : null;

    await fs.mkdir(path.dirname(CSV_FILE), { recursive: true });
    const output = lines.length > 0 ? `${lines.join('\n')}\n` : '';
    await fs.writeFile(CSV_FILE, output);

    // Also delete from database if enabled
    if (this.dbEnabled && this.db && deletedSku) {
      try {
        await this.db.product.deleteMany({
          where: { sku: deletedSku }
        });
      } catch (error) {
        console.warn('Database delete failed (CSV deleted successfully)');
      }
    }

    return { deleted: true, sku: deletedSku, remainingLastSku };
  }

  /**
   * Check if database mode is enabled
   */
  isDatabaseEnabled(): boolean {
    return this.dbEnabled && this.db !== null;
  }

  /**
   * Get database instance (for marketplace integrations)
   */
  getDatabase(): any {
    return this.db;
  }

  /**
   * Disconnect from database
   */
  async disconnect(): Promise<void> {
    if (this.db) {
      await this.db.$disconnect();
    }
  }
}
