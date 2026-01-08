# CLI ↔ Web Platform Integration Guide

This guide explains how to integrate your existing Inventory Processing CLI with the new Cross-Listing Web Platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED SYSTEM                            │
├──────────────────────────┬──────────────────────────────────┤
│   CLI Tool (Terminal)    │   Web Platform (Browser)         │
├──────────────────────────┼──────────────────────────────────┤
│ • Inventory intake       │ • Multi-marketplace listing      │
│ • Batch processing       │ • Cross-listing automation       │
│ • Label printing         │ • Analytics dashboard            │
│ • Photo management       │ • Marketplace management         │
│ • SKU generation         │ • AI-powered optimization        │
└──────────────┬───────────┴────────────┬─────────────────────┘
               │                        │
               └────────────┬───────────┘
                            │
                ┌───────────▼──────────┐
                │  PostgreSQL Database  │
                │  (Shared Data Layer)  │
                └──────────────────────┘
```

## Integration Benefits

### What You Keep
✅ All existing CLI features (batch processing, label printing, photo intake)
✅ Familiar terminal-based workflow
✅ Thermal printer integration
✅ SKU generation system
✅ CSV export capabilities (for backwards compatibility)

### What You Gain
🚀 Multi-marketplace cross-listing (10+ platforms)
🚀 Web-based dashboard for analytics
🚀 Auto-delist on sale detection
🚀 AI-powered listing optimization
🚀 Real-time inventory sync
🚀 Bulk operations across marketplaces

## Setup Instructions

### Step 1: Install Dependencies

```bash
cd /Users/connorodea/Library/Mobile\ Documents/com~apple~CloudDocs/UPSCALED2026/Upscaled_inv_processing

# Install Prisma and API client dependencies
npm install --save @prisma/client axios
npm install --save-dev prisma
```

### Step 2: Link to Shared Prisma Schema

```bash
# Create symbolic link to web platform's Prisma schema
ln -sf ../upscaled-crosslist/prisma ./prisma

# Generate Prisma client for CLI
npx prisma generate
```

### Step 3: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
# DATABASE_URL should match the web platform's database
```

### Step 4: Update package.json

Add these scripts to your CLI's `package.json`:

```json
{
  "scripts": {
    "db:generate": "npx prisma generate",
    "db:studio": "npx prisma studio",
    "sync": "tsx src/scripts/syncToDatabase.ts"
  }
}
```

### Step 5: Test Database Connection

```bash
# Test connection to PostgreSQL
npm run db:generate

# Open Prisma Studio to view data
npm run db:studio
```

## Migration Path

### Option A: Gradual Migration (Recommended)

**Phase 1: Dual-Write Mode**
- CLI writes to both CSV and PostgreSQL
- Web platform reads from PostgreSQL
- CSV remains as backup

**Phase 2: Database-First Mode**
- CLI writes only to PostgreSQL
- CSV export available on demand
- Full feature parity

**Phase 3: Full Integration**
- CLI calls web platform API for cross-listing
- Unified analytics and reporting
- CSV deprecated

### Option B: Instant Migration

Run the migration script to move all existing CSV data to PostgreSQL:

```bash
cd ../upscaled-crosslist
npx tsx prisma/migration/csv-to-postgres.ts
```

## Using the Integration

### In the CLI (New Features)

After integration, your CLI will have new menu options:

```
╔═══════════════════════════════════════════════╗
║     INVENTORY PROCESSING SYSTEM               ║
║     + Multi-Marketplace Cross-Listing         ║  ← NEW!
╚═══════════════════════════════════════════════╝

Main Menu:
  1. Add Product (saves to PostgreSQL automatically)
  2. Print Labels
  3. Export Batch
  4. eBay Listing
  5. 🆕 Cross-List to Multiple Marketplaces        ← NEW!
  6. 🆕 View Marketplace Status                    ← NEW!
  7. 🆕 AI-Enhanced Listing                        ← NEW!
  8. Settings
  9. Exit
```

### New CLI Commands

**Cross-List a Product:**
```typescript
// In your CLI
import { WebPlatformClient } from './api/webPlatformClient.js';

const client = new WebPlatformClient();
await client.crossListProduct({
  sku: 'LN-DEN001-B1UID001-BIN001',
  marketplaces: ['ebay', 'poshmark', 'mercari'],
  priceOverrides: {
    'poshmark': 49.99,
    'mercari': 45.00
  }
});
```

**Check Marketplace Status:**
```typescript
const status = await client.getMarketplaceStatus('LN-DEN001-B1UID001-BIN001');
console.log(status);
// [
//   { marketplace: 'ebay', status: 'active', listingUrl: '...' },
//   { marketplace: 'poshmark', status: 'pending' }
// ]
```

## Code Changes Required

### 1. Update `src/index.ts` (Main CLI)

Add new imports:
```typescript
import { PrismaAdapter } from './database/prismaAdapter.js';
import { WebPlatformClient } from './api/webPlatformClient.js';
```

Update constructor:
```typescript
constructor() {
  // Existing code...
  this.prismaAdapter = new PrismaAdapter();  // NEW
  this.webClient = new WebPlatformClient();  // NEW
}
```

### 2. Update `src/csvStorage.ts` (or create wrapper)

Add database fallback:
```typescript
import { PrismaAdapter } from './database/prismaAdapter.js';

export class UnifiedStorage {
  private csv: CSVStorage;
  private db: PrismaAdapter;
  private useDatabase: boolean;

  constructor() {
    this.csv = new CSVStorage();
    this.db = new PrismaAdapter();
    this.useDatabase = process.env.USE_DATABASE === 'true';
  }

  async save(product: Product) {
    if (this.useDatabase) {
      await this.db.saveProduct(product);
    }
    // Also save to CSV for backup (dual-write)
    await this.csv.save(product);
  }
}
```

### 3. Add New Menu Options

In `src/index.ts`, add new menu items:

```typescript
private async showMainMenu(): Promise<void> {
  const choices = [
    { name: '📦 Add Product', value: 'add' },
    { name: '🖨️  Print Labels', value: 'print' },
    { name: '📋 Export Batch', value: 'export' },
    { name: '🔗 eBay Listing', value: 'ebay' },
    new inquirer.Separator('━━ 🆕 Multi-Marketplace Features ━━'),  // NEW
    { name: '🌐 Cross-List to Marketplaces', value: 'crosslist' }, // NEW
    { name: '📊 View Marketplace Status', value: 'status' },       // NEW
    { name: '🤖 AI-Enhanced Listing', value: 'ai-enrich' },        // NEW
    new inquirer.Separator('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),
    { name: '⚙️  Settings', value: 'settings' },
    { name: '🚪 Exit', value: 'exit' }
  ];

  const { action } = await inquirer.prompt([{
    type: 'list',
    name: 'action',
    message: 'What would you like to do?',
    choices
  }]);

  switch (action) {
    case 'crosslist':
      await this.handleCrossListing();  // NEW
      break;
    case 'status':
      await this.handleMarketplaceStatus();  // NEW
      break;
    case 'ai-enrich':
      await this.handleAIEnrichment();  // NEW
      break;
    // ... existing cases
  }
}
```

### 4. Implement New Handlers

```typescript
private async handleCrossListing(): Promise<void> {
  // Get recent products or let user select
  const products = await this.prismaAdapter.getProductsByBatch(
    this.batchManager.getCurrentBatchNumber().toString()
  );

  if (products.length === 0) {
    console.log(chalk.yellow('No products in current batch'));
    return;
  }

  // Show product selection
  const { selectedSku } = await inquirer.prompt([{
    type: 'list',
    name: 'selectedSku',
    message: 'Select product to cross-list:',
    choices: products.map(p => ({
      name: `${p.sku} - ${p.manufacturer} ${p.model} (${p.grade})`,
      value: p.sku
    }))
  }]);

  // Select marketplaces
  const { marketplaces } = await inquirer.prompt([{
    type: 'checkbox',
    name: 'marketplaces',
    message: 'Select marketplaces:',
    choices: [
      { name: 'eBay', value: 'ebay', checked: true },
      { name: 'Poshmark', value: 'poshmark' },
      { name: 'Mercari', value: 'mercari' },
      { name: 'Shopify', value: 'shopify' },
      { name: 'Depop', value: 'depop' },
      { name: 'Facebook Marketplace', value: 'facebook' }
    ]
  }]);

  // Trigger cross-listing
  const spinner = ora('Cross-listing product...').start();

  const result = await this.webClient.crossListProduct({
    sku: selectedSku,
    marketplaces
  });

  if (result.success) {
    spinner.succeed(chalk.green('✓ Product cross-listed successfully'));
    console.log(chalk.cyan(`Job ID: ${result.jobId}`));
  } else {
    spinner.fail(chalk.red('✗ Cross-listing failed'));
    console.log(chalk.red(result.error));
  }
}

private async handleMarketplaceStatus(): Promise<void> {
  const { sku } = await inquirer.prompt([{
    type: 'input',
    name: 'sku',
    message: 'Enter SKU to check status:'
  }]);

  const spinner = ora('Fetching marketplace status...').start();
  const statuses = await this.webClient.getMarketplaceStatus(sku);
  spinner.stop();

  if (statuses.length === 0) {
    console.log(chalk.yellow('No marketplace listings found for this SKU'));
    return;
  }

  const table = new Table({
    head: ['Marketplace', 'Status', 'Price', 'Listing URL'],
    colWidths: [15, 12, 10, 50]
  });

  for (const status of statuses) {
    table.push([
      status.marketplace.toUpperCase(),
      status.status === 'active' ? chalk.green('● Active') : chalk.yellow('○ Pending'),
      status.price ? `$${status.price}` : '-',
      status.listingUrl || '-'
    ]);
  }

  console.log(table.toString());
}
```

## Workflow Examples

### Example 1: Add Product + Auto Cross-List

```bash
# In CLI
1. Add Product
   └─ Automatically saves to PostgreSQL ✓
   └─ Label printed ✓
   └─ Photo intake triggered ✓

2. Cross-List to Multiple Marketplaces
   └─ Select: eBay, Poshmark, Mercari
   └─ Web platform handles listing ✓
   └─ Returns job ID for tracking ✓

3. View Marketplace Status
   └─ Shows live status on all platforms ✓
```

### Example 2: Batch Processing Workflow

```bash
# Process entire batch in CLI (existing workflow)
$ npm run dev
> Add 50 products to Batch 2
> Print all labels
> Export batch to CSV

# Cross-list entire batch via web platform
$ curl -X POST http://localhost:3002/api/products/bulk/cross-list \
  -H "Content-Type: application/json" \
  -d '{"batchNumber": "B2", "marketplaces": ["ebay", "poshmark"]}'
```

## Troubleshooting

### Issue: "Cannot connect to database"

**Solution:**
```bash
# Ensure Docker containers are running
docker ps | grep upscaled

# If not running, start them
cd ../upscaled-crosslist
docker-compose up -d

# Test connection
npx prisma db pull
```

### Issue: "Web platform not responding"

**Solution:**
```bash
# Check if web platform is running
curl http://localhost:3002/api/health

# If not, start it
cd ../upscaled-crosslist
npm run dev
```

### Issue: "Prisma client not generated"

**Solution:**
```bash
# Regenerate Prisma client
npx prisma generate
```

## Feature Comparison

| Feature | CLI Only | CLI + Web Platform |
|---------|----------|-------------------|
| Inventory Intake | ✅ | ✅ |
| Label Printing | ✅ | ✅ |
| Photo Management | ✅ | ✅ |
| eBay Listing | ✅ | ✅ |
| Multi-Marketplace | ❌ | ✅ |
| Auto-Delist | ❌ | ✅ |
| Analytics Dashboard | ❌ | ✅ |
| AI Optimization | ❌ | ✅ |
| Bulk Cross-Listing | ❌ | ✅ |
| Real-time Sync | ❌ | ✅ |

## Next Steps

1. **Test Integration**: Run the CLI with database mode enabled
2. **Migrate Data**: Import existing CSV data to PostgreSQL
3. **Add Menu Options**: Integrate new cross-listing features
4. **Train Team**: Document new workflow for team members
5. **Monitor Performance**: Track sync latency and job queue

## Support

- **CLI Issues**: Check `Upscaled_inv_processing/` logs
- **Web Platform Issues**: Check `upscaled-crosslist/` logs
- **Database Issues**: Check Docker logs: `docker logs upscaled-postgres`

## Summary

This integration gives you the best of both worlds:
- Keep your proven CLI workflow for inventory intake
- Gain powerful web-based multi-marketplace features
- Share data seamlessly between both tools
- Scale to 10+ marketplaces without changing your process
