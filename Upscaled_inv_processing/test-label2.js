import { createCanvas } from 'canvas';
import fs from 'fs/promises';

console.log('Creating canvas...');
const canvas = createCanvas(406, 203, 'image');
const ctx = canvas.getContext('2d');

console.log('Drawing white rectangle...');
ctx.fillStyle = 'white';
ctx.fillRect(0, 0, 406, 203);

console.log('Drawing black border...');
ctx.strokeStyle = 'black';
ctx.lineWidth = 5;
ctx.strokeRect(10, 10, 386, 183);

console.log('Drawing text...');
ctx.fillStyle = 'black';
ctx.font = 'bold 30px Arial';
ctx.textAlign = 'center';
ctx.textBaseline = 'middle';
ctx.fillText('HELLO WORLD', 203, 101);

console.log('Converting to buffer...');
const buffer = canvas.toBuffer('image/png', { compressionLevel: 3, filters: canvas.PNG_FILTER_NONE });

console.log('Saving file...');
await fs.writeFile('test-output2.png', buffer);

console.log('✓ Done! Check test-output2.png');
