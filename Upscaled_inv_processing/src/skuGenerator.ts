import { Grade } from './types.js';

export function generateSKU(
  grade: Grade,
  location: string,
  batchId: string,
  warehouseTag?: string
): string {
  const parts = [grade, location, batchId];

  if (warehouseTag) {
    parts.push(warehouseTag);
  }

  return parts.join('-');
}

export function validateGrade(input: string): Grade | null {
  const validGrades: Grade[] = ['LN', 'VG', 'G', 'AC', 'SA'];
  const upper = input.toUpperCase() as Grade;
  return validGrades.includes(upper) ? upper : null;
}
