import express from 'express';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { ThermalPrinter } from './printer.js';

const app = express();
const port = Number.parseInt(process.env.PRINT_AGENT_PORT || '8788', 10);
const printer = new ThermalPrinter();
const baseDir = process.env.PRINT_AGENT_DIR || path.join(os.homedir(), 'Library', 'Application Support', 'UpscaledPrintAgent');

app.use(express.json({ limit: '5mb' }));

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.post('/print', async (req, res) => {
  const { imageBase64, filename } = req.body as { imageBase64?: string; filename?: string };
  if (!imageBase64) {
    res.status(400).json({ error: 'imageBase64 is required' });
    return;
  }

  const buffer = Buffer.from(imageBase64, 'base64');
  const outputDir = path.join(baseDir, 'print_jobs');
  await fs.mkdir(outputDir, { recursive: true });
  const safeName = filename && filename.endsWith('.png') ? filename : `label_${Date.now()}.png`;
  const filePath = path.join(outputDir, safeName);
  await fs.writeFile(filePath, buffer);

  try {
    await printer.print(filePath);
    res.json({ status: 'printed', filePath });
  } catch (error) {
    res.status(500).json({ error: `Print failed: ${error}` });
  }
});

(async () => {
  await printer.initialize();
  app.listen(port, () => {
    console.log(`Print agent listening on port ${port}`);
  });
})();
