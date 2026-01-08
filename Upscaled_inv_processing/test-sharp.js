import sharp from 'sharp';

// Create a simple label with sharp
const width = 406;
const height = 203;

// Create white background with black text using SVG
const svg = `
<svg width="${width}" height="${height}">
  <rect width="${width}" height="${height}" fill="white"/>
  <text x="50%" y="50%"
        font-family="Arial"
        font-size="24"
        font-weight="bold"
        fill="black"
        text-anchor="middle"
        dominant-baseline="middle">
    LN-DEN001-B1UID001-BIN001
  </text>
</svg>
`;

await sharp(Buffer.from(svg))
  .png()
  .toFile('test-sharp-output.png');

console.log('✓ Sharp label created: test-sharp-output.png');
