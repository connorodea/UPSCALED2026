import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export class ThermalPrinter {
  private printerName: string | null = null;

  async initialize(): Promise<void> {
    // Try to detect thermal printer
    try {
      const { stdout } = await execAsync('lpstat -p -d');
      const lines = stdout.split('\n');

      // Look for a thermal printer or use default
      for (const line of lines) {
        if (line.includes('printer') && !line.includes('disabled')) {
          const match = line.match(/printer (\S+)/);
          if (match) {
            this.printerName = match[1];
            break;
          }
        }
      }

      if (!this.printerName) {
        // Try to get default printer
        const defaultMatch = stdout.match(/system default destination: (\S+)/);
        if (defaultMatch) {
          this.printerName = defaultMatch[1];
        }
      }
    } catch (error) {
      console.warn('Warning: Could not detect printer. Printing may fail.');
    }
  }

  async print(imagePath: string): Promise<void> {
    if (!this.printerName) {
      throw new Error('No printer configured. Please set up a CUPS printer.');
    }

    try {
      // Use lp command to print the image
      // Options:
      // -d: specify printer
      // -o fit-to-page: scale image to fit label
      // -o media=Custom.51x25mm: set label size (2" x 1")
      const command = `lp -d "${this.printerName}" -o fit-to-page -o media=Custom.51x25mm "${imagePath}"`;

      await execAsync(command);
      console.log(`✓ Label printed successfully to ${this.printerName}`);
    } catch (error) {
      throw new Error(`Failed to print label: ${error}`);
    }
  }

  getPrinterName(): string | null {
    return this.printerName;
  }

  async listPrinters(): Promise<string[]> {
    try {
      const { stdout } = await execAsync('lpstat -p');
      const lines = stdout.split('\n').filter(line => line.startsWith('printer'));
      return lines.map(line => {
        const match = line.match(/printer (\S+)/);
        return match ? match[1] : '';
      }).filter(Boolean);
    } catch (error) {
      return [];
    }
  }
}
