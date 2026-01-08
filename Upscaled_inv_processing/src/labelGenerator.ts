import sharp from 'sharp';
import bwipjs from 'bwip-js';
import fs from 'fs/promises';
import path from 'path';
import { Product, LabelConfig } from './types.js';

export class LabelGenerator {
  private config: LabelConfig;

  constructor() {
    // 2" x 1" label at 203 DPI (standard thermal printer)
    this.config = {
      width: 51,   // mm
      height: 25,  // mm
      dpi: 203
    };
  }

  private mmToPixels(mm: number): number {
    return Math.round((mm / 25.4) * this.config.dpi);
  }

  private async generateLabelForSku(sku: string, timestamp?: Date): Promise<string> {
    const width = this.mmToPixels(this.config.width);
    const height = this.mmToPixels(this.config.height);

    const timestampText = (timestamp ?? new Date()).toISOString();

    // Extract batch ID from SKU (format: GRADE-LOCATION-BATCHID-TAG)
    const parts = sku.split('-');
    const batchId = parts[2] || ''; // B1UID011

    // Generate barcode as PNG buffer using bwip-js
    let barcodeBuffer: Buffer | null = null;
    try {
      barcodeBuffer = await bwipjs.toBuffer({
        bcid: 'code128',
        text: sku,
        scale: 2,
        height: 10,
        includetext: false,
        backgroundcolor: 'ffffff',
        barcolor: '000000'
      });
    } catch (error) {
      console.error('Barcode generation failed:', error);
    }

    // Convert barcode to base64 data URI
    const barcodeDataUrl = barcodeBuffer
      ? `data:image/png;base64,${barcodeBuffer.toString('base64')}`
      : '';

    // Create label using SVG with text and barcode
    const svg = `
      <svg width="${width}" height="${height}">
        <rect width="${width}" height="${height}" fill="white"/>

        <!-- Timestamp -->
        <text x="50%" y="18"
              font-family="Arial, sans-serif"
              font-size="16"
              font-weight="normal"
              fill="black"
              text-anchor="middle"
              dominant-baseline="middle">
          ${timestampText}
        </text>

        <!-- Batch ID - Large and Bold -->
        <text x="50%" y="50"
              font-family="Arial, sans-serif"
              font-size="56"
              font-weight="900"
              fill="black"
              text-anchor="middle"
              dominant-baseline="middle">
          ${batchId}
        </text>

        <!-- Full SKU Text - Smaller -->
        <text x="50%" y="90"
              font-family="Arial, sans-serif"
              font-size="24"
              font-weight="normal"
              fill="black"
              text-anchor="middle"
              dominant-baseline="middle">
          ${sku}
        </text>

        <!-- Barcode Image -->
        ${barcodeDataUrl ? `
        <image x="15" y="105" width="${width - 30}" height="90"
               href="${barcodeDataUrl}" preserveAspectRatio="xMidYMid meet"/>
        ` : ''}
      </svg>
    `;

    // Save label
    const labelDir = path.join(process.cwd(), 'labels');
    await fs.mkdir(labelDir, { recursive: true });

    const labelPath = path.join(labelDir, `${sku}.png`);

    await sharp(Buffer.from(svg))
      .png()
      .toFile(labelPath);

    return labelPath;
  }

  async generateLabel(product: Product): Promise<string> {
    return this.generateLabelForSku(product.sku, product.timestamp);
  }

  async generateLabelFromSku(sku: string): Promise<string> {
    return this.generateLabelForSku(sku);
  }

  async generatePidUidLabel(pidUid: string, manifestId: string): Promise<string> {
    const width = this.mmToPixels(this.config.width);
    const height = this.mmToPixels(this.config.height);

    let barcodeBuffer: Buffer | null = null;
    try {
      barcodeBuffer = await bwipjs.toBuffer({
        bcid: 'code128',
        text: pidUid,
        scale: 2,
        height: 10,
        includetext: false,
        backgroundcolor: 'ffffff',
        barcolor: '000000'
      });
    } catch (error) {
      console.error('Barcode generation failed:', error);
    }

    const barcodeDataUrl = barcodeBuffer
      ? `data:image/png;base64,${barcodeBuffer.toString('base64')}`
      : '';

    const svg = `
      <svg width="${width}" height="${height}">
        <rect width="${width}" height="${height}" fill="white"/>

        <text x="50%" y="18"
              font-family="Arial, sans-serif"
              font-size="18"
              font-weight="normal"
              fill="black"
              text-anchor="middle"
              dominant-baseline="middle">
          ${manifestId}
        </text>

        <text x="50%" y="55"
              font-family="Arial, sans-serif"
              font-size="50"
              font-weight="900"
              fill="black"
              text-anchor="middle"
              dominant-baseline="middle">
          ${pidUid}
        </text>

        ${barcodeDataUrl ? `
        <image x="15" y="95" width="${width - 30}" height="90"
               href="${barcodeDataUrl}" preserveAspectRatio="xMidYMid meet"/>
        ` : ''}
      </svg>
    `;

    const labelDir = path.join(process.cwd(), 'labels', 'piduid');
    await fs.mkdir(labelDir, { recursive: true });

    const labelPath = path.join(labelDir, `${pidUid}.png`);

    await sharp(Buffer.from(svg))
      .png()
      .toFile(labelPath);

    return labelPath;
  }
}
