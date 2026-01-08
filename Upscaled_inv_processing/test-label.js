import { createCanvas } from 'canvas';
import fs from 'fs/promises';

// Test label generation
const width = 406;  // 2" at 203 DPI
const height = 203; // 1" at 203 DPI

const canvas = createCanvas(width, height);
const ctx = canvas.getContext('2d');

// White background
ctx.fillStyle = '#FFFFFF';
ctx.fillRect(0, 0, width, height);

// Black text
ctx.fillStyle = '#000000';
ctx.textAlign = 'center';
ctx.textBaseline = 'middle';
ctx.font = 'bold 24px Arial';

// Draw test text
ctx.fillText('TEST-LABEL-123', width / 2, height / 2);

// Save
const buffer = canvas.toBuffer('image/png');
await fs.writeFile('test-output.png', buffer);

console.log('✓ Test label created: test-output.png');
