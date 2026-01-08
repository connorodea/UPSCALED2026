import path from 'path';

const DATA_DIR = path.join(process.cwd(), 'data');
const BATCH_FILE_REGEX = /^B(\d+)-([A-Z0-9]+)\.csv$/i;

export function getBatchFileName(batchNumber: number, location: string): string {
  return `B${batchNumber}-${location}.csv`;
}

export function getBatchFilePath(batchNumber: number, location: string): string {
  return path.join(DATA_DIR, getBatchFileName(batchNumber, location));
}

export function parseBatchFileName(fileName: string): { batchNumber: number; location: string } | null {
  const match = fileName.match(BATCH_FILE_REGEX);
  if (!match) {
    return null;
  }

  return {
    batchNumber: Number.parseInt(match[1], 10),
    location: match[2].toUpperCase()
  };
}

export function isBatchFileForLocation(fileName: string, location: string): boolean {
  const parsed = parseBatchFileName(fileName);
  if (!parsed) {
    return false;
  }
  return parsed.location === location.toUpperCase();
}
