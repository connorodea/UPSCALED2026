import fs from 'fs/promises';
import path from 'path';
import { BatchState } from './types.js';

const DATA_DIR = path.join(process.cwd(), 'data');
const LEGACY_BATCH_STATE_FILE = path.join(DATA_DIR, 'batch-state.json');
const LOCATION_STATE_FILE = path.join(DATA_DIR, 'location.json');
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
    const location = await this.loadLocation();
    await this.loadStateForLocation(location);
    await this.persistState(this.state.location, this.state);
    await this.persistLocation(this.state.location);
  }

  async save(): Promise<void> {
    await this.persistState(this.state.location, this.state);
    await this.persistLocation(this.state.location);
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
    if (location === this.state.location) {
      return;
    }

    await this.persistState(this.state.location, this.state);
    await this.loadStateForLocation(location);
    await this.persistState(this.state.location, this.state);
    await this.persistLocation(this.state.location);
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

  private getBatchStateFile(location: string): string {
    return path.join(DATA_DIR, `batch-state-${location}.json`);
  }

  private getDefaultState(location: string): BatchState {
    return {
      currentBatchNumber: 1,
      currentItemNumber: 1,
      batchSize: BATCH_SIZE,
      location,
      lastSku: undefined
    };
  }

  private async readJsonFile<T>(filePath: string): Promise<T | null> {
    try {
      const data = await fs.readFile(filePath, 'utf-8');
      return JSON.parse(data) as T;
    } catch (error) {
      return null;
    }
  }

  private async loadLocation(): Promise<string> {
    const locationState = await this.readJsonFile<{ location?: string }>(LOCATION_STATE_FILE);
    if (locationState?.location) {
      return locationState.location;
    }

    const legacyState = await this.readJsonFile<Partial<BatchState>>(LEGACY_BATCH_STATE_FILE);
    if (legacyState?.location) {
      return legacyState.location;
    }

    return DEFAULT_LOCATION;
  }

  private async loadStateForLocation(location: string): Promise<void> {
    const defaultState = this.getDefaultState(location);
    const batchStateFile = this.getBatchStateFile(location);
    const batchState = await this.readJsonFile<Partial<BatchState>>(batchStateFile);

    if (batchState) {
      this.state = { ...defaultState, ...batchState, location };
      return;
    }

    const legacyState = await this.readJsonFile<Partial<BatchState>>(LEGACY_BATCH_STATE_FILE);
    if (legacyState && (legacyState.location ?? location) === location) {
      this.state = { ...defaultState, ...legacyState, location };
      return;
    }

    this.state = defaultState;
  }

  private async persistState(location: string, state: BatchState): Promise<void> {
    await fs.mkdir(DATA_DIR, { recursive: true });
    await fs.writeFile(this.getBatchStateFile(location), JSON.stringify(state, null, 2));
  }

  private async persistLocation(location: string): Promise<void> {
    await fs.mkdir(DATA_DIR, { recursive: true });
    await fs.writeFile(LOCATION_STATE_FILE, JSON.stringify({ location }, null, 2));
  }
}
