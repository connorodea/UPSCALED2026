import fs from 'fs/promises';
import path from 'path';

export interface ManifestRecord {
  manifestId: string;
  palletId: string;
  unitCount: number;
  createdAt: string;
  auctionId?: string;
  auctionTitle?: string;
  auctionUrl?: string;
  manifestUrl?: string;
  lotPriceValue?: number;
  currentBidValue?: number;
  msrpValue?: number;
  retailValue?: number;
  itemsCountValue?: number;
  condition?: string;
  warehouse?: string;
  auctionEnd?: string;
  sourceSite?: string;
  sourceYear?: string;
  sourcePath?: string;
}

const MANIFEST_FILE = path.join(process.cwd(), 'data', 'manifests.json');

export class ManifestManager {
  private manifests: ManifestRecord[] = [];

  async load(): Promise<void> {
    try {
      const data = await fs.readFile(MANIFEST_FILE, 'utf-8');
      this.manifests = JSON.parse(data);
    } catch (error: any) {
      if (error?.code !== 'ENOENT') {
        throw error;
      }
      this.manifests = [];
      await this.save();
    }
  }

  getManifestCount(): number {
    return this.manifests.length;
  }

  async save(): Promise<void> {
    await fs.mkdir(path.dirname(MANIFEST_FILE), { recursive: true });
    await fs.writeFile(MANIFEST_FILE, JSON.stringify(this.manifests, null, 2));
  }

  getNextPalletId(): string {
    const max = this.manifests.reduce((acc, manifest) => {
      const match = manifest.palletId.match(/^P(\d+)$/i);
      if (!match) {
        return acc;
      }
      const value = Number.parseInt(match[1], 10);
      return Number.isNaN(value) ? acc : Math.max(acc, value);
    }, 0);

    return `P${max + 1}`;
  }

  async createManifest(
    manifestId: string,
    unitCount: number,
    auctionData?: Partial<ManifestRecord>
  ): Promise<ManifestRecord> {
    const existing = this.manifests.find(
      record => record.manifestId.toUpperCase() === manifestId.toUpperCase()
    );
    if (existing) {
      if (auctionData) {
        Object.assign(existing, auctionData);
        await this.save();
      }
      return existing;
    }

    const palletId = this.getNextPalletId();
    const record: ManifestRecord = {
      manifestId,
      palletId,
      unitCount,
      createdAt: new Date().toISOString(),
      ...(auctionData ? auctionData : {})
    };

    this.manifests.push(record);
    await this.save();
    return record;
  }

  getManifestByPalletId(palletId: string): ManifestRecord | undefined {
    return this.manifests.find(record => record.palletId.toUpperCase() === palletId.toUpperCase());
  }
}
