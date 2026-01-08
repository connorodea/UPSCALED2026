export type Grade = 'LN' | 'VG' | 'G' | 'AC' | 'SA';

export interface Product {
  grade: Grade;
  upc?: string;
  manufacturer?: string;
  model?: string;
  warehouseTag?: string;
  notes?: string;
  palletId?: string;
  unitId?: string;
  pidUid?: string;
  manifestId?: string;
  sku: string;
  batchId: string;
  location: string;
  timestamp: Date;
}

export interface BatchState {
  currentBatchNumber: number;
  currentItemNumber: number;
  batchSize: number;
  location: string;
  lastSku?: string;
}

export interface LabelConfig {
  width: number;  // in mm
  height: number; // in mm
  dpi: number;
}
