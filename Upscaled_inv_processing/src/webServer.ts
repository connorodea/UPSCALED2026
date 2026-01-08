import express from 'express';
import type { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import fs from 'fs/promises';
import path from 'path';
import { spawn } from 'child_process';
import crypto from 'crypto';
import { BatchManager } from './batchManager.js';
import { CSVStorage } from './csvStorage.js';
import { LabelGenerator } from './labelGenerator.js';
import { ThermalPrinter } from './printer.js';
import { BatchExporter } from './batchExporter.js';
import { ManifestManager, ManifestRecord } from './manifestManager.js';
import { generateSKU } from './skuGenerator.js';
import { Product, Grade } from './types.js';
import { isBatchFileForLocation } from './batchFiles.js';

const app = express();
const port = Number.parseInt(process.env.PORT || '8787', 10);
const staticRoot = path.join(process.cwd(), 'ui');
const webPassword = process.env.UPSCALED_WEB_PASSWORD || '';
const usersConfig = process.env.UPSCALED_USERS || '';
const printMode = process.env.PRINT_MODE || 'local';
const printProxyUrl = process.env.PRINT_PROXY_URL || '';

const batchManager = new BatchManager();
const csvStorage = new CSVStorage();
const labelGenerator = new LabelGenerator();
const printer = new ThermalPrinter();
const batchExporter = new BatchExporter();
const manifestManager = new ManifestManager();

const VALID_GRADES = new Set<Grade>(['LN', 'VG', 'G', 'AC', 'SA']);

app.use(cors());
app.use(express.json({ limit: '2mb' }));
app.use(express.static(staticRoot));

const api = express.Router();
app.use('/api', api);

type UserRecord = {
  username: string;
  password: string;
  role: 'admin' | 'staff';
};

const userTokens = new Map<string, UserRecord>();
const users: UserRecord[] = (() => {
  if (!usersConfig) {
    return [];
  }
  try {
    const parsed = JSON.parse(usersConfig);
    if (Array.isArray(parsed)) {
      return parsed.filter(
        (entry) => entry?.username && entry?.password && entry?.role
      ) as UserRecord[];
    }
  } catch {
    return [];
  }
  return [];
})();

type AuthContext = {
  user?: UserRecord;
};

function requireRole(role: 'admin' | 'staff') {
  return (req: express.Request, res: express.Response, next: express.NextFunction) => {
    const auth = (req as AuthContext).user;
    if (!auth) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }
    if (role === 'admin' && auth.role !== 'admin') {
      res.status(403).json({ error: 'Forbidden' });
      return;
    }
    next();
  };
}

api.use((req: Request, res: Response, next: NextFunction) => {
  if (!webPassword && users.length === 0) {
    next();
    return;
  }

  if (req.path === '/login') {
    next();
    return;
  }

  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : '';
  if (!token) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }

  if (webPassword && token === webPassword) {
    (req as AuthContext).user = { username: 'legacy', password: '', role: 'admin' };
    next();
    return;
  }

  const user = userTokens.get(token);
  if (!user) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  (req as AuthContext).user = user;
  next();
});

async function initialize(): Promise<void> {
  await batchManager.load();
  await manifestManager.load();
  if (printMode === 'local') {
    await printer.initialize();
  }
}

function normalizePidUid(value: string): string {
  return value.trim().toUpperCase();
}

async function findProjectRoot(start: string): Promise<string | null> {
  let current = path.resolve(start);
  while (true) {
    const candidate = path.join(current, '01_SOURCING');
    try {
      const stat = await fs.stat(candidate);
      if (stat.isDirectory()) {
        return current;
      }
    } catch {
      // keep walking
    }
    const parent = path.dirname(current);
    if (parent === current) {
      break;
    }
    current = parent;
  }
  return null;
}

async function findIndexFiles(root: string): Promise<string[]> {
  const results: string[] = [];
  try {
    const entries = await fs.readdir(root, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(root, entry.name);
      if (entry.isDirectory()) {
        const nested = await findIndexFiles(fullPath);
        results.push(...nested);
      } else if (entry.isFile() && entry.name === 'index.jsonl') {
        results.push(fullPath);
      }
    }
  } catch {
    return results;
  }
  return results;
}

function extractYear(value: string): string | undefined {
  const match = value.match(/\b(20\d{2})\b/);
  return match ? match[1] : undefined;
}

async function lookupAuctionForManifest(manifestId: string): Promise<Partial<ManifestRecord> | null> {
  const normalized = manifestId.trim().toUpperCase();
  const root = await findProjectRoot(process.cwd());
  if (!root) {
    return null;
  }
  const auctionsRoot = path.join(root, '01_SOURCING', 'Auctions');
  const indexFiles = await findIndexFiles(auctionsRoot);

  for (const indexPath of indexFiles) {
    let data = '';
    try {
      data = await fs.readFile(indexPath, 'utf-8');
    } catch {
      continue;
    }
    const lines = data.split(/\r?\n/).filter(line => line.trim());
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        const auctionId = String(entry.auction_id || entry.lot_id || '').toUpperCase();
        const manifestUrl = String(entry.manifest_url || '').toUpperCase();
        if (auctionId === normalized || manifestUrl.includes(normalized)) {
          return {
            auctionId: entry.auction_id || entry.lot_id,
            auctionTitle: entry.title,
            auctionUrl: entry.url,
            manifestUrl: entry.manifest_url,
            lotPriceValue: entry.lot_price_value,
            currentBidValue: entry.current_bid_value,
            msrpValue: entry.msrp_value,
            retailValue: entry.retail_value_value,
            itemsCountValue: entry.items_count_value,
            condition: entry.condition,
            warehouse: entry.warehouse,
            auctionEnd: entry.auction_end,
            sourceSite: entry.site,
            sourceYear: extractYear(indexPath),
            sourcePath: indexPath
          };
        }
      } catch {
        continue;
      }
    }
  }

  return null;
}

function getInventoryHeaders(): string[] {
  return [
    'SKU',
    'Grade',
    'Location',
    'Batch ID',
    'Warehouse Tag',
    'UPC',
    'Manufacturer',
    'Model',
    'Notes',
    'Timestamp',
    'Manifest ID',
    'Pallet ID',
    'Unit ID',
    'PID-UID'
  ];
}

async function loadInventoryRows(): Promise<Record<string, string>[]> {
  const inventoryPath = path.join(process.cwd(), 'data', 'inventory.csv');
  let data = '';
  try {
    data = await fs.readFile(inventoryPath, 'utf-8');
  } catch {
    return [];
  }

  const lines = data.split(/\r?\n/).filter(line => line.trim());
  if (!lines.length) {
    return [];
  }

  const headers = getInventoryHeaders();
  const firstLine = lines[0].split(',');
  const hasHeader = firstLine.some((value) => value.trim().toUpperCase() === 'SKU');
  const dataLines = hasHeader ? lines.slice(1) : lines;
  const rows: Record<string, string>[] = [];

  for (const line of dataLines) {
    const cells = line.split(',');
    const row: Record<string, string> = {};
    headers.forEach((header, idx) => {
      row[header] = cells[idx] || '';
    });
    rows.push(row);
  }

  return rows;
}

api.get('/download/labels/:filename', async (req: Request, res: Response) => {
  const filename = String(req.params.filename || '');
  if (!filename.endsWith('.png')) {
    res.status(400).json({ error: 'Invalid label file' });
    return;
  }
  const filePath = path.join(process.cwd(), 'labels', filename);
  res.download(filePath, filename);
});

api.get('/status', async (_req: Request, res: Response) => {
  const status = {
    batchNumber: batchManager.getCurrentBatchNumber(),
    itemNumber: batchManager.getCurrentItemNumber(),
    itemsRemaining: batchManager.getItemsRemainingInBatch(),
    batchId: batchManager.getCurrentBatchId(),
    location: batchManager.getLocation()
  };
  res.json(status);
});

api.post('/login', async (req: Request, res: Response) => {
  if (!webPassword && users.length === 0) {
    res.json({ ok: true });
    return;
  }

  const { password, username } = req.body as { password?: string; username?: string };
  if (webPassword && password === webPassword) {
    res.json({ ok: true, token: webPassword, role: 'admin' });
    return;
  }

  if (!username || !password) {
    res.status(401).json({ error: 'Invalid credentials' });
    return;
  }

  const matched = users.find(
    (user) => user.username === username && user.password === password
  );
  if (!matched) {
    res.status(401).json({ error: 'Invalid credentials' });
    return;
  }

  const token = crypto.randomBytes(24).toString('hex');
  userTokens.set(token, matched);
  res.json({ ok: true, token, role: matched.role });
});

api.get('/inventory', async (_req: Request, res: Response) => {
  const rows = await loadInventoryRows();
  res.json({ headers: getInventoryHeaders(), rows });
});

api.get('/batches', async (_req: Request, res: Response) => {
  const dataDir = path.join(process.cwd(), 'data');
  let files: string[] = [];
  try {
    files = await fs.readdir(dataDir);
  } catch {
    files = [];
  }
  const location = batchManager.getLocation();
  const batchFiles = files.filter(file => isBatchFileForLocation(file, location));
  res.json({ batchFiles, currentBatch: batchManager.getCurrentBatchNumber(), location });
});

api.get('/metrics', async (_req: Request, res: Response) => {
  const inventoryRows = await loadInventoryRows();
  const totalProcessed = inventoryRows.length;
  const today = new Date().toISOString().slice(0, 10);
  const processedToday = inventoryRows.filter(row =>
    String(row['Timestamp'] || '').startsWith(today)
  ).length;

  const manifestCount = manifestManager.getManifestCount();

  const hubRoot = await findProjectRoot(process.cwd());
  let unprocessedCount = 0;
  if (hubRoot) {
    const unprocessedPath = path.join(hubRoot, '01_SOURCING', 'Inventory_Hub', 'inventory_unprocessed.csv');
    try {
      const contents = await fs.readFile(unprocessedPath, 'utf-8');
      const lines = contents.split(/\r?\n/).filter(line => line.trim());
      unprocessedCount = Math.max(lines.length - 1, 0);
    } catch {
      unprocessedCount = 0;
    }
  }

  res.json({
    totalProcessed,
    processedToday,
    manifestCount,
    unprocessedCount
  });
});

api.get('/print-agent/status', async (_req: Request, res: Response) => {
  if (printMode === 'local') {
    res.json({
      status: printer.getPrinterName() ? 'local_ready' : 'local_not_ready',
      mode: 'local'
    });
    return;
  }

  if (printMode === 'disabled') {
    res.json({ status: 'disabled', mode: 'disabled' });
    return;
  }

  if (!printProxyUrl) {
    res.json({ status: 'missing_url', mode: 'proxy' });
    return;
  }

  try {
    const healthUrl = new URL('/health', printProxyUrl).toString();
    const response = await fetch(healthUrl, { method: 'GET' });
    res.json({ status: response.ok ? 'ok' : 'unreachable', mode: 'proxy' });
  } catch {
    res.json({ status: 'unreachable', mode: 'proxy' });
  }
});

api.get('/download/inventory.csv', async (_req: Request, res: Response) => {
  const inventoryPath = path.join(process.cwd(), 'data', 'inventory.csv');
  res.download(inventoryPath, 'inventory.csv');
});

api.get('/download/hub/processed', async (_req: Request, res: Response) => {
  const root = await findProjectRoot(process.cwd());
  if (!root) {
    res.status(404).json({ error: 'Hub not found' });
    return;
  }
  const filePath = path.join(root, '01_SOURCING', 'Inventory_Hub', 'inventory_processed.csv');
  res.download(filePath, 'inventory_processed.csv');
});

api.get('/download/hub/unprocessed', async (_req: Request, res: Response) => {
  const root = await findProjectRoot(process.cwd());
  if (!root) {
    res.status(404).json({ error: 'Hub not found' });
    return;
  }
  const filePath = path.join(root, '01_SOURCING', 'Inventory_Hub', 'inventory_unprocessed.csv');
  res.download(filePath, 'inventory_unprocessed.csv');
});

async function sendToPrintProxy(labelPath: string): Promise<void> {
  if (!printProxyUrl) {
    return;
  }
  const buffer = await fs.readFile(labelPath);
  const payload = {
    imageBase64: buffer.toString('base64'),
    filename: path.basename(labelPath)
  };

  await fetch(printProxyUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

api.post('/manifest', requireRole('staff'), async (req, res) => {
  const { manifestId, unitCount, printLabels } = req.body as {
    manifestId?: string;
    unitCount?: number | string;
    printLabels?: boolean;
  };

  if (!manifestId || !unitCount) {
    res.status(400).json({ error: 'manifestId and unitCount are required' });
    return;
  }

  const parsedCount = Number.parseInt(String(unitCount), 10);
  if (!Number.isFinite(parsedCount) || parsedCount <= 0) {
    res.status(400).json({ error: 'unitCount must be a positive number' });
    return;
  }

  const auctionData = await lookupAuctionForManifest(String(manifestId));
  const record = await manifestManager.createManifest(
    String(manifestId).trim().toUpperCase(),
    parsedCount,
    auctionData || undefined
  );

  const pid = record.palletId;
  const pidUids = Array.from({ length: parsedCount }, (_, i) => `${pid}-ID${i + 1}`);
  const labels: string[] = [];

  for (const pidUid of pidUids) {
    const labelPath = await labelGenerator.generatePidUidLabel(pidUid, record.manifestId);
    labels.push(labelPath);
    if (printLabels) {
      try {
        if (printMode === 'proxy') {
          await sendToPrintProxy(labelPath);
        } else if (printMode === 'local') {
          await printer.print(labelPath);
        }
      } catch {
        // Ignore print failures in API context
      }
    }
  }

  res.json({ record, pidUids, labels });
});

api.post('/product', requireRole('staff'), async (req, res) => {
  const {
    pidUid,
    grade,
    upc,
    manufacturer,
    model,
    warehouseTag,
    notes,
    printLabel
  } = req.body as {
    pidUid?: string;
    grade?: Grade;
    upc?: string;
    manufacturer?: string;
    model?: string;
    warehouseTag?: string;
    notes?: string;
    printLabel?: boolean;
  };

  if (!pidUid || !grade || !VALID_GRADES.has(grade)) {
    res.status(400).json({ error: 'pidUid and valid grade are required' });
    return;
  }

  const normalizedPid = normalizePidUid(pidUid);
  const [palletId, unitId] = normalizedPid.split('-', 2);
  if (!palletId || !unitId) {
    res.status(400).json({ error: 'pidUid must look like P1-ID1' });
    return;
  }

  const manifest = manifestManager.getManifestByPalletId(palletId);
  const manifestId = manifest?.manifestId;

  const batchId = batchManager.getCurrentBatchId();
  const location = batchManager.getLocation();
  const sku = generateSKU(
    grade,
    location,
    batchId,
    warehouseTag ? String(warehouseTag).trim().toUpperCase() : undefined
  );
  await batchManager.setLastSku(sku);

  const product: Product = {
    grade,
    upc: upc || undefined,
    manufacturer: manufacturer || undefined,
    model: model || undefined,
    warehouseTag: warehouseTag || undefined,
    notes: notes || undefined,
    palletId,
    unitId,
    pidUid: normalizedPid,
    manifestId,
    sku,
    batchId,
    location,
    timestamp: new Date()
  };

  await csvStorage.saveProduct(product);
  const labelPath = await labelGenerator.generateLabel(product);

  let printed = false;
  if (printLabel) {
    try {
      if (printMode === 'proxy') {
        await sendToPrintProxy(labelPath);
        printed = true;
      } else if (printMode === 'local') {
        await printer.print(labelPath);
        printed = true;
      }
    } catch {
      printed = false;
    }
  }

  const completedBatch = await batchManager.incrementItem();
  if (completedBatch !== null) {
    await batchExporter.exportBatch(completedBatch, location);
  }

  const labelDownload = `/api/download/labels/${path.basename(labelPath)}`;
  res.json({ product, labelPath, labelDownload, printed, completedBatch });
});

api.post('/batch/export', requireRole('admin'), async (req, res) => {
  const { batchNumber } = req.body as { batchNumber?: number | string };
  const resolved = batchNumber ? Number.parseInt(String(batchNumber), 10) : batchManager.getCurrentBatchNumber();
  if (!Number.isFinite(resolved) || resolved <= 0) {
    res.status(400).json({ error: 'batchNumber must be a positive number' });
    return;
  }

  await batchExporter.exportBatch(resolved, batchManager.getLocation());
  res.json({ batchNumber: resolved });
});

api.post('/hub/build', requireRole('admin'), async (_req, res) => {
  const root = await findProjectRoot(process.cwd());
  if (!root) {
    res.status(500).json({ error: 'Project root not found' });
    return;
  }

  const scriptPath = path.join(
    root,
    '08_AUTOMATION',
    'CLI_Tools',
    'auction_scraper',
    'build_master_manifest.py'
  );

  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const child = spawn(pythonCmd, [scriptPath]);

  child.on('close', (code) => {
    if (code === 0) {
      res.json({ status: 'ok' });
    } else {
      res.status(500).json({ error: 'Hub build failed' });
    }
  });
});

app.get('*', (_req: Request, res: Response) => {
  res.sendFile(path.join(staticRoot, 'index.html'));
});

initialize().then(() => {
  app.listen(port, () => {
    console.log(`Upscaled Inventory Web listening on port ${port}`);
  });
});
