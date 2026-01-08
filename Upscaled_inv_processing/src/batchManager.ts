import fs from 'fs/promises';
import path from 'path';
import { BatchState } from './types.js';

const BATCH_STATE_FILE = path.join(process.cwd(), 'data', 'batch-state.json');
const BATCH_SIZE = 50;
const DEFAULT_LOCATION = 'DEN001';

export class BatchManager {
  private state: BatchState;

  constructor() {
    this.state = {
      currentBatchNumber: 1,
      currentItemNumber: 1,
      batchSize: BATCH_SIZE,
      location: DEFAULT_LOCATION,
      lastSku: undefined
    };
  }

  async load(): Promise<void> {
    try {
      const data = await fs.readFile(BATCH_STATE_FILE, 'utf-8');
      const parsed = JSON.parse(data);
      this.state = { ...this.state, ...parsed };
    } catch (error) {
      // If file doesn't exist, use default state
      await this.save();
    }
  }

  async save(): Promise<void> {
    await fs.mkdir(path.dirname(BATCH_STATE_FILE), { recursive: true });
    await fs.writeFile(BATCH_STATE_FILE, JSON.stringify(this.state, null, 2));
  }

  getCurrentBatchId(): string {
    const batchNum = this.state.currentBatchNumber.toString().padStart(1, '0');
    const itemNum = this.state.currentItemNumber.toString().padStart(3, '0');
    return `B${batchNum}UID${itemNum}`;
  }

  async incrementItem(): Promise<number | null> {
    this.state.currentItemNumber++;

    let completedBatch: number | null = null;

    if (this.state.currentItemNumber > this.state.batchSize) {
      // Batch is complete
      completedBatch = this.state.currentBatchNumber;

      // Start new batch
      this.state.currentBatchNumber++;
      this.state.currentItemNumber = 1;
    }

    await this.save();

    return completedBatch; // Returns batch number if completed, null otherwise
  }

  getCurrentBatchNumber(): number {
    return this.state.currentBatchNumber;
  }

  getCurrentItemNumber(): number {
    return this.state.currentItemNumber;
  }

  getItemsRemainingInBatch(): number {
    return this.state.batchSize - this.state.currentItemNumber + 1;
  }

  getLocation(): string {
    return this.state.location;
  }


  async setLocation(location: string): Promise<void> {
    this.state.location = location;
    await this.save();
  }

  getLastSku(): string | undefined {
    return this.state.lastSku;
  }

  async setLastSku(sku: string | null): Promise<void> {
    this.state.lastSku = sku ?? undefined;
    await this.save();
  }

  async reset(): Promise<void> {
    this.state.currentBatchNumber = 1;
    this.state.currentItemNumber = 1;
    this.state.lastSku = undefined;
    await this.save();
  }

  async forceNextBatch(): Promise<void> {
    this.state.currentBatchNumber++;
    this.state.currentItemNumber = 1;
    await this.save();
  }
}
