import fs from 'fs/promises';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import { EBAY_DEFAULTS, GRADE_TO_CONDITION, GRADE_PRICE_MULTIPLIER } from './ebayConfig.js';

const execAsync = promisify(exec);

export class EbayIntegration {
  private ebayAutolisterPath: string;
  private basePrices: Map<string, number>;

  constructor() {
    this.ebayAutolisterPath = path.join(process.cwd(), 'EbayAutolister');
    this.basePrices = new Map([
      // Add base prices for common products - update as needed
      ['Samsung', 100.00],
      ['Apple', 200.00],
      ['default', 50.00]
    ]);
  }

  async listBatchOnEbay(batchNumber: number): Promise<void> {
    try {
      const batchFile = path.join(process.cwd(), 'data', `B${batchNumber}.csv`);

      // Check if batch file exists
      try {
        await fs.access(batchFile);
      } catch (error) {
        throw new Error(`Batch file B${batchNumber}.csv not found`);
      }

      // Read and transform batch CSV to eBay format
      const ebayCSV = await this.transformToEbayFormat(batchFile);

      // Create eBay-formatted CSV file
      const ebayCSVPath = path.join(process.cwd(), 'data', `B${batchNumber}_ebay.csv`);
      await fs.writeFile(ebayCSVPath, ebayCSV);

      console.log(`✓ Created eBay CSV: ${ebayCSVPath}`);

      // Call eBay autolister CLI
      console.log(`📤 Listing Batch ${batchNumber} on eBay...`);

      const command = `cd ${this.ebayAutolisterPath} && python3 cli.py process "../data/B${batchNumber}_ebay.csv" --create-offers`;

      const { stdout, stderr } = await execAsync(command);

      if (stderr && !stderr.includes('WARNING')) {
        console.error('eBay listing errors:', stderr);
      }

      console.log('eBay autolister output:', stdout);

    } catch (error) {
      throw new Error(`eBay listing failed: ${error}`);
    }
  }

  private async transformToEbayFormat(batchFilePath: string): Promise<string> {
    const content = await fs.readFile(batchFilePath, 'utf-8');
    const lines = content.trim().split('\n');

    if (lines.length === 0) {
      throw new Error('Batch file is empty');
    }

    // eBay CSV header
    const ebayHeader = 'sku,title,description,condition,category_id,price,quantity,brand,mpn,weight,dimensions,images';

    // Transform each product line
    const ebayLines = lines.slice(1).map((line, index) => {
      const fields = this.parseCSVLine(line);

      if (fields.length < 8) {
        console.warn(`Skipping invalid line ${index + 1}`);
        return null;
      }

      const [sku, grade, location, batchId, warehouseTag, upc, manufacturer, model, notes] = fields;

      // Build eBay listing
      const brand = manufacturer || 'Generic';
      const mpn = model || sku;
      const condition = GRADE_TO_CONDITION[grade] || 'USED_GOOD';

      // Calculate price based on manufacturer and grade
      const basePrice = this.basePrices.get(brand) || this.basePrices.get('default')!;
      const multiplier = GRADE_PRICE_MULTIPLIER[grade] || 0.70;
      const price = (basePrice * multiplier).toFixed(2);

      // Create title
      const title = `${brand} ${model || 'Product'} - ${grade} Condition - ${sku}`.substring(0, 80);

      // Create description
      const description = [
        `${brand} ${model || 'Product'}`,
        `Condition: ${grade}`,
        `SKU: ${sku}`,
        notes ? `Notes: ${notes}` : '',
        `Location: ${location}`,
        warehouseTag ? `Warehouse: ${warehouseTag}` : ''
      ].filter(Boolean).join(' | ');

      // Return eBay CSV line
      return [
        sku,
        `"${title}"`,
        `"${description}"`,
        condition,
        EBAY_DEFAULTS.categoryId,
        price,
        EBAY_DEFAULTS.quantity,
        `"${brand}"`,
        `"${mpn}"`,
        EBAY_DEFAULTS.weightLbs,
        `"${EBAY_DEFAULTS.dimensions}"`,
        '""' // Empty images for now
      ].join(',');
    }).filter(Boolean);

    return [ebayHeader, ...ebayLines].join('\n');
  }

  private parseCSVLine(line: string): string[] {
    const fields: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];

      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        fields.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    fields.push(current.trim());
    return fields;
  }
}
