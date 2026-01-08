import fs from 'fs/promises';
import path from 'path';
import { createObjectCsvWriter } from 'csv-writer';

const INVENTORY_CSV = path.join(process.cwd(), 'data', 'inventory.csv');
const DATA_DIR = path.join(process.cwd(), 'data');

export class BatchExporter {
  async exportBatch(batchNumber: number): Promise<void> {
    try {
      // Read the main inventory CSV
      const csvContent = await fs.readFile(INVENTORY_CSV, 'utf-8');
      const lines = csvContent.split('\n');

      if (lines.length < 2) {
        console.log('No data to export for batch', batchNumber);
        return;
      }

      // Get header
      const header = lines[0];

      // Filter lines for this batch (B{number}UID)
      const batchPrefix = `B${batchNumber}UID`;
      const batchLines = lines.filter(line =>
        line.includes(batchPrefix) && line.trim() !== ''
      );

      if (batchLines.length === 0) {
        console.log(`No items found for batch ${batchNumber}`);
        return;
      }

      // Create batch CSV file
      const batchFile = path.join(DATA_DIR, `B${batchNumber}.csv`);
      const batchContent = [header, ...batchLines].join('\n');

      await fs.writeFile(batchFile, batchContent);

      console.log(`✓ Batch ${batchNumber} exported to ${batchFile} (${batchLines.length} items)`);
    } catch (error) {
      console.error(`Failed to export batch ${batchNumber}:`, error);
    }
  }
}
