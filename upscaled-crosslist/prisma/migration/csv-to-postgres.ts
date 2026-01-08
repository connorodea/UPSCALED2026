/**
 * CSV to PostgreSQL Migration Script
 *
 * Migrates existing inventory data from Upscaled_inv_processing CSV files
 * to the new PostgreSQL database.
 *
 * Preserves:
 * - All 40+ product records from data/inventory.csv
 * - Current batch state (Batch 2, Item 49)
 * - SKU format and batch tracking
 * - Product grading system
 *
 * Usage:
 *   npx tsx prisma/migration/csv-to-postgres.ts
 */

import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';

const prisma = new PrismaClient();

// Paths to existing data files
const LEGACY_PATH = path.join(process.cwd(), '..', 'Upscaled_inv_processing');
const CSV_PATH = path.join(LEGACY_PATH, 'data', 'inventory.csv');
const BATCH_STATE_PATH = path.join(LEGACY_PATH, 'data', 'batch-state.json');

interface CSVProduct {
  sku: string;
  grade: string;
  location: string;
  batchId: string;
  warehouseTag: string;
  upc?: string;
  manufacturer?: string;
  model?: string;
  notes?: string;
  timestamp: string;
}

interface BatchState {
  currentBatchNumber: number;
  currentItemNumber: number;
  batchSize: number;
  location: string;
  lastSku: string;
}

/**
 * Parse CSV line into structured product data
 */
function parseCSVLine(line: string): CSVProduct | null {
  const parts = line.split(',');

  if (parts.length < 8) {
    console.warn(`Skipping malformed line: ${line}`);
    return null;
  }

  // CSV format: SKU, Grade, Location, BatchID, WarehouseTag, UPC, Manufacturer, Model, Notes, Timestamp
  const [
    sku,
    grade,
    location,
    batchId,
    warehouseTag,
    upc,
    manufacturer,
    model,
    ...rest
  ] = parts;

  // Handle notes and timestamp (notes may contain commas, so we need to rejoin)
  let notes = '';
  let timestamp = '';

  if (rest.length >= 2) {
    // Last item is timestamp, everything before is notes
    timestamp = rest[rest.length - 1];
    notes = rest.slice(0, rest.length - 1).join(',').trim();
  } else if (rest.length === 1) {
    timestamp = rest[0];
  }

  return {
    sku: sku.trim(),
    grade: grade.trim(),
    location: location.trim(),
    batchId: batchId.trim(),
    warehouseTag: warehouseTag.trim(),
    upc: upc?.trim() || undefined,
    manufacturer: manufacturer?.trim() || undefined,
    model: model?.trim() || undefined,
    notes: notes || undefined,
    timestamp: timestamp.trim(),
  };
}

/**
 * Read and parse CSV file
 */
function readCSV(): CSVProduct[] {
  if (!fs.existsSync(CSV_PATH)) {
    console.error(`CSV file not found at: ${CSV_PATH}`);
    console.error('Make sure the Upscaled_inv_processing directory exists.');
    return [];
  }

  const csvContent = fs.readFileSync(CSV_PATH, 'utf-8');
  const lines = csvContent.split('\n').filter(line => line.trim());

  const products: CSVProduct[] = [];

  for (const line of lines) {
    const product = parseCSVLine(line);
    if (product) {
      products.push(product);
    }
  }

  console.log(`✓ Parsed ${products.length} products from CSV`);
  return products;
}

/**
 * Read batch state JSON
 */
function readBatchState(): BatchState | null {
  if (!fs.existsSync(BATCH_STATE_PATH)) {
    console.warn(`Batch state file not found at: ${BATCH_STATE_PATH}`);
    return null;
  }

  const stateContent = fs.readFileSync(BATCH_STATE_PATH, 'utf-8');
  const state = JSON.parse(stateContent) as BatchState;

  console.log(`✓ Current batch state: Batch ${state.currentBatchNumber}, Item ${state.currentItemNumber}`);
  return state;
}

/**
 * Extract batch numbers from products
 */
function extractBatchNumbers(products: CSVProduct[]): Set<string> {
  const batches = new Set<string>();

  for (const product of products) {
    // Extract batch number from batchId (e.g., "B1UID001" → "B1")
    const match = product.batchId.match(/^(B\d+)/);
    if (match) {
      batches.add(match[1]);
    }
  }

  return batches;
}

/**
 * Migrate batches to database
 */
async function migrateBatches(products: CSVProduct[], batchState: BatchState | null) {
  const batchNumbers = extractBatchNumbers(products);

  console.log(`\n📦 Migrating ${batchNumbers.size} batches...`);

  for (const batchNumber of Array.from(batchNumbers).sort()) {
    const batchProducts = products.filter(p => p.batchId.startsWith(batchNumber));
    const isCurrentBatch = batchState && batchNumber === `B${batchState.currentBatchNumber}`;

    const batch = await prisma.batch.upsert({
      where: { batchNumber },
      update: {
        totalItems: batchProducts.length,
        processedItems: batchProducts.length,
        status: isCurrentBatch ? 'active' : 'completed',
        completedAt: isCurrentBatch ? null : new Date(),
      },
      create: {
        batchNumber,
        location: batchState?.location || 'DEN001',
        totalItems: batchProducts.length,
        processedItems: batchProducts.length,
        status: isCurrentBatch ? 'active' : 'completed',
        completedAt: isCurrentBatch ? null : new Date(),
      },
    });

    console.log(`  ✓ ${batchNumber}: ${batchProducts.length} items (${batch.status})`);
  }
}

/**
 * Migrate products to database
 */
async function migrateProducts(products: CSVProduct[]) {
  console.log(`\n📦 Migrating ${products.length} products...`);

  let successCount = 0;
  let errorCount = 0;

  for (const product of products) {
    try {
      await prisma.product.upsert({
        where: { sku: product.sku },
        update: {
          grade: product.grade,
          location: product.location,
          batchId: product.batchId.match(/^(B\d+)/)?.[1] || 'B1',
          warehouseTag: product.warehouseTag || null,
          upc: product.upc || null,
          manufacturer: product.manufacturer || null,
          model: product.model || null,
          notes: product.notes || null,
          updatedAt: new Date(product.timestamp),
        },
        create: {
          sku: product.sku,
          grade: product.grade,
          location: product.location,
          batchId: product.batchId.match(/^(B\d+)/)?.[1] || 'B1',
          warehouseTag: product.warehouseTag || null,
          upc: product.upc || null,
          manufacturer: product.manufacturer || null,
          model: product.model || null,
          notes: product.notes || null,
          createdAt: new Date(product.timestamp),
        },
      });

      successCount++;
    } catch (error) {
      console.error(`  ✗ Error migrating ${product.sku}:`, error);
      errorCount++;
    }
  }

  console.log(`\n✓ Successfully migrated ${successCount} products`);
  if (errorCount > 0) {
    console.log(`✗ Failed to migrate ${errorCount} products`);
  }
}

/**
 * Validate migration results
 */
async function validateMigration(expectedCount: number) {
  console.log('\n🔍 Validating migration...');

  const productCount = await prisma.product.count();
  const batchCount = await prisma.batch.count();

  console.log(`  Products in database: ${productCount} (expected: ${expectedCount})`);
  console.log(`  Batches in database: ${batchCount}`);

  if (productCount !== expectedCount) {
    console.warn(`  ⚠️  Warning: Product count mismatch!`);
    return false;
  }

  // Check a sample product
  const sampleProduct = await prisma.product.findFirst({
    include: {
      batch: true,
    },
  });

  if (sampleProduct) {
    console.log(`\n  Sample product:`);
    console.log(`    SKU: ${sampleProduct.sku}`);
    console.log(`    Grade: ${sampleProduct.grade}`);
    console.log(`    Manufacturer: ${sampleProduct.manufacturer}`);
    console.log(`    Model: ${sampleProduct.model}`);
    console.log(`    Batch: ${sampleProduct.batch?.batchNumber} (${sampleProduct.batch?.status})`);
  }

  console.log('\n✅ Migration validation complete!');
  return true;
}

/**
 * Main migration function
 */
async function main() {
  console.log('🚀 Starting CSV to PostgreSQL migration...\n');

  try {
    // Step 1: Read CSV data
    const products = readCSV();
    if (products.length === 0) {
      console.error('❌ No products found in CSV. Exiting.');
      process.exit(1);
    }

    // Step 2: Read batch state
    const batchState = readBatchState();

    // Step 3: Migrate batches
    await migrateBatches(products, batchState);

    // Step 4: Migrate products
    await migrateProducts(products);

    // Step 5: Validate migration
    await validateMigration(products.length);

    console.log('\n✅ Migration completed successfully!');
    console.log('\n📊 Next steps:');
    console.log('  1. Run: npx prisma studio (to view your data)');
    console.log('  2. Start the dev server: npm run dev');
    console.log('  3. Visit: http://localhost:3000/dashboard');

  } catch (error) {
    console.error('\n❌ Migration failed:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();
