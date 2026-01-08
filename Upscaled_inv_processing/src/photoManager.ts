import fs from 'fs/promises';
import path from 'path';
import { Dirent } from 'fs';
import { stat } from 'fs/promises';
import inquirer from 'inquirer';
import chalk from 'chalk';

type PhotoConfig = {
  enabled: boolean;
  watchDir?: string;
  intakeDir: string;
  outputDir: string;
  minCount: number;
  idleMs: number;
  timeoutMs: number;
  ocrEnabled: boolean;
};

const IMAGE_EXTENSIONS = new Set([
  '.jpg',
  '.jpeg',
  '.png',
  '.heic',
  '.tif',
  '.tiff',
  '.webp'
]);

export class PhotoManager {
  private config: PhotoConfig;

  constructor() {
    const enabledEnv = (process.env.PHOTO_STEP || '').toLowerCase();
    const enabled = enabledEnv !== '0' && enabledEnv !== 'false';
    const watchDir = process.env.PHOTO_WATCH_DIR;
    const intakeDir = process.env.PHOTO_INTAKE_DIR || path.join(process.cwd(), 'data', 'photo-intake');
    const outputDir = process.env.PHOTO_OUTPUT_DIR || path.join(process.cwd(), 'data', 'photos');
    const minCount = Number.parseInt(process.env.PHOTO_MIN_COUNT || '1', 10);
    const idleMs = Number.parseInt(process.env.PHOTO_IDLE_MS || '1500', 10);
    const timeoutMs = Number.parseInt(process.env.PHOTO_TIMEOUT_MS || '120000', 10);
    const ocrEnabledEnv = (process.env.PHOTO_OCR || 'true').toLowerCase();
    const ocrEnabled = ocrEnabledEnv !== '0' && ocrEnabledEnv !== 'false';

    this.config = {
      enabled,
      watchDir,
      intakeDir,
      outputDir,
      minCount: Number.isNaN(minCount) ? 1 : minCount,
      idleMs: Number.isNaN(idleMs) ? 1500 : idleMs,
      timeoutMs: Number.isNaN(timeoutMs) ? 120000 : timeoutMs,
      ocrEnabled
    };
  }

  isEnabled(): boolean {
    return this.config.enabled;
  }

  async captureForId(labelId: string): Promise<string[]> {
    if (!this.config.enabled) {
      return [];
    }

    if (!this.config.watchDir) {
      await inquirer.prompt([
        {
          type: 'input',
          name: 'photoAck',
          message: chalk.bold(
            'Apply label, take photos (label first/last), then press Enter to continue.'
          ),
          prefix: '📸'
        }
      ]);
      return [];
    }

    await inquirer.prompt([
      {
        type: 'input',
        name: 'photoStart',
        message: chalk.bold(
          `Place item with label in frame. Press Enter to start photo capture for ${labelId}.`
        ),
        prefix: '📸'
      }
    ]);

    const newFiles = await this.waitForPhotos();
    if (newFiles.length === 0) {
      console.log(chalk.yellow('No new photos detected. Skipping photo intake.'));
      return [];
    }

    const saved = await this.storePhotos(labelId, newFiles);
    console.log(chalk.green(`Saved ${saved.length} photo(s) for ${labelId}`));
    return saved;
  }

  getIntakeDir(): string {
    return this.config.intakeDir;
  }

  async runPidUidIntakeSession(options?: { interactive?: boolean; continuous?: boolean }): Promise<void> {
    const interactive = options?.interactive !== false;
    const continuous = options?.continuous === true;
    const intakeDir = this.config.intakeDir;
    await fs.mkdir(intakeDir, { recursive: true });

    const instructions = [
      `Drop new photos into: ${intakeDir}`,
      'Take product photos, then take a close-up of the PID-UID label to mark the end.'
    ].join('\n');
    console.log(chalk.cyan(instructions));

    let keepRunning = true;
    const processed = new Set<string>();
    const buffer: string[] = [];
    let warnedDecoder = false;
    let lastBufferAt = 0;

    while (keepRunning) {
      const incoming = await this.sortByMtime(await this.listImageFiles(intakeDir));
      for (const file of incoming) {
        if (processed.has(file)) {
          continue;
        }
        processed.add(file);

        const pidUid = await this.detectPidUid(file);
        if (!pidUid) {
          buffer.push(file);
          lastBufferAt = Date.now();
          continue;
        }

        const saved = await this.storePhotos(pidUid, buffer);
        await this.storeMarkerPhoto(pidUid, file);
        buffer.length = 0;

        console.log(chalk.green(`Linked ${saved.length} photo(s) to ${pidUid}`));

        if (interactive && !continuous) {
          const { continueIntake } = await inquirer.prompt([
            {
              type: 'confirm',
              name: 'continueIntake',
              message: chalk.bold('Continue watching for the next product?'),
              default: true,
              prefix: '📸'
            }
          ]);

          if (!continueIntake) {
            keepRunning = false;
            break;
          }
        }
      }

      if (buffer.length > 0 && Date.now() - lastBufferAt >= this.config.timeoutMs) {
        if (interactive) {
          const { manualPidUid } = await inquirer.prompt([
            {
              type: 'input',
              name: 'manualPidUid',
              message: chalk.bold('No marker found. Enter PID-UID to assign buffered photos (or leave blank):'),
              prefix: '🧷',
              filter: (input: string) => input.trim().toUpperCase(),
              validate: (input: string) =>
                input.trim() === '' || /^P\d+-ID\d+$/i.test(input.trim()) || 'Use format P1-ID1'
            }
          ]);

          if (manualPidUid) {
            const saved = await this.storePhotos(manualPidUid, buffer);
            buffer.length = 0;
            console.log(chalk.green(`Manually linked ${saved.length} photo(s) to ${manualPidUid}`));
          }
        } else {
          await this.storeUnassigned(buffer);
          buffer.length = 0;
          console.log(chalk.yellow('No marker detected. Buffered photos moved to _unassigned.'));
        }
        lastBufferAt = Date.now();
      }

      if (keepRunning) {
        if (buffer.length === 0 && incoming.length === 0) {
          if (!warnedDecoder) {
            const decoderReady = await this.isDecoderAvailable();
            if (!decoderReady) {
              warnedDecoder = true;
              console.log(chalk.yellow('Barcode decoder not available. Run `npm install` to enable auto-detect.'));
            }
          }
          await this.sleep(800);
        } else {
          await this.sleep(200);
        }
      }
    }

    if (buffer.length > 0) {
      await this.storeUnassigned(buffer);
      console.log(chalk.yellow('Unassigned photos were moved to _unassigned.'));
    }
  }

  private async waitForPhotos(): Promise<string[]> {
    const watchDir = this.config.watchDir as string;
    const baseline = new Set(await this.listImageFiles(watchDir));
    const discovered = new Set<string>();

    const start = Date.now();
    let lastNew = Date.now();

    while (Date.now() - start < this.config.timeoutMs) {
      const current = await this.listImageFiles(watchDir);
      for (const file of current) {
        if (!baseline.has(file) && !discovered.has(file)) {
          discovered.add(file);
          lastNew = Date.now();
        }
      }

      const idleFor = Date.now() - lastNew;
      if (discovered.size >= this.config.minCount && idleFor >= this.config.idleMs) {
        break;
      }

      await this.sleep(500);
    }

    return this.sortByMtime(Array.from(discovered));
  }

  private async storePhotos(labelId: string, files: string[]): Promise<string[]> {
    const labelDir = path.join(this.config.outputDir, labelId);
    await fs.mkdir(labelDir, { recursive: true });

    const saved: string[] = [];
    for (let i = 0; i < files.length; i++) {
      const source = files[i];
      await this.waitForStableSize(source);
      const ext = path.extname(source).toLowerCase() || '.jpg';
      const target = path.join(labelDir, `${labelId}_${String(i + 1).padStart(2, '0')}${ext}`);
      await this.moveFile(source, target);
      saved.push(target);
    }

    return saved;
  }

  private async storeMarkerPhoto(labelId: string, file: string): Promise<string> {
    const labelDir = path.join(this.config.outputDir, labelId);
    await fs.mkdir(labelDir, { recursive: true });
    const ext = path.extname(file).toLowerCase() || '.jpg';
    const target = path.join(labelDir, `${labelId}_marker${ext}`);
    await this.waitForStableSize(file);
    await this.moveFile(file, target);
    return target;
  }

  private async detectPidUid(filePath: string): Promise<string | null> {
    const text = await this.decodeBarcode(filePath);
    if (!text) {
      const ocrText = await this.decodeTextViaOcr(filePath);
      if (!ocrText) {
        return null;
      }
      const ocrMatch = ocrText.match(/P\d+-ID\d+/i);
      return ocrMatch ? ocrMatch[0].toUpperCase() : null;
    }
    const match = text.match(/P\d+-ID\d+/i);
    return match ? match[0].toUpperCase() : null;
  }

  private async isDecoderAvailable(): Promise<boolean> {
    try {
      await import('@zxing/library');
      return true;
    } catch (error) {
      return false;
    }
  }

  private async decodeBarcode(filePath: string): Promise<string | null> {
    try {
      const zxing = await import('@zxing/library') as any;
      const { RGBLuminanceSource, BinaryBitmap, HybridBinarizer, MultiFormatReader } = zxing;
      const sharpModule = await import('sharp');
      const sharp = sharpModule.default;
      const { data, info } = await sharp(filePath)
        .ensureAlpha()
        .raw()
        .toBuffer({ resolveWithObject: true });

      const luminance = new RGBLuminanceSource(new Uint8ClampedArray(data), info.width, info.height);
      const binaryBitmap = new BinaryBitmap(new HybridBinarizer(luminance));
      const reader = new MultiFormatReader();
      const result = reader.decode(binaryBitmap);
      return result?.getText?.() || null;
    } catch (error) {
      return null;
    }
  }

  private async decodeTextViaOcr(filePath: string): Promise<string | null> {
    if (!this.config.ocrEnabled) {
      return null;
    }

    try {
      const tesseract = await import('tesseract.js');
      const result = await tesseract.recognize(filePath, 'eng');
      return result?.data?.text || null;
    } catch (error) {
      return null;
    }
  }

  private async storeUnassigned(files: string[]): Promise<string> {
    const folderName = `batch_${new Date().toISOString().replace(/[:.]/g, '-')}`;
    const targetDir = path.join(this.config.outputDir, '_unassigned', folderName);
    await fs.mkdir(targetDir, { recursive: true });

    for (const file of files) {
      await this.waitForStableSize(file);
      const ext = path.extname(file).toLowerCase() || '.jpg';
      const target = path.join(targetDir, path.basename(file, ext) + ext);
      await this.moveFile(file, target);
    }

    return targetDir;
  }

  private async listImageFiles(dir: string): Promise<string[]> {
    let entries: Dirent[];
    try {
      entries = await fs.readdir(dir, { withFileTypes: true });
    } catch (error) {
      console.log(chalk.yellow(`Photo watch folder not found: ${dir}`));
      return [];
    }

    return entries
      .filter(entry => entry.isFile())
      .map(entry => path.join(dir, entry.name))
      .filter(file => IMAGE_EXTENSIONS.has(path.extname(file).toLowerCase()));
  }

  private async sortByMtime(files: string[]): Promise<string[]> {
    const withTimes = await Promise.all(files.map(async file => {
      const info = await stat(file);
      return { file, time: info.mtimeMs };
    }));
    withTimes.sort((a, b) => a.time - b.time);
    return withTimes.map(item => item.file);
  }

  private async waitForStableSize(filePath: string): Promise<void> {
    let lastSize = -1;
    for (let i = 0; i < 6; i++) {
      const info = await stat(filePath);
      if (info.size === lastSize) {
        return;
      }
      lastSize = info.size;
      await this.sleep(300);
    }
  }

  private async moveFile(source: string, target: string): Promise<void> {
    try {
      await fs.rename(source, target);
      return;
    } catch (error: any) {
      if (error?.code !== 'EXDEV') {
        throw error;
      }
    }

    await fs.copyFile(source, target);
    await fs.unlink(source);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
