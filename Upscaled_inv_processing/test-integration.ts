/**
 * Integration Test Script
 * Tests CLI connection to web platform and database
 */

import { PrismaClient } from '@prisma/client';
import axios from 'axios';
import chalk from 'chalk';

const prisma = new PrismaClient();

async function testDatabaseConnection() {
  console.log('\n🔍 Testing database connection...');

  try {
    await prisma.$connect();
    console.log(chalk.green('✓ Connected to PostgreSQL'));

    // Test query
    const batchCount = await prisma.batch.count();
    const productCount = await prisma.product.count();

    console.log(chalk.cyan(`  • Found ${batchCount} batches`));
    console.log(chalk.cyan(`  • Found ${productCount} products`));

    return true;
  } catch (error: any) {
    console.log(chalk.red('✗ Database connection failed:'), error.message);
    return false;
  }
}

async function testWebPlatformConnection() {
  console.log('\n🔍 Testing web platform connection...');

  try {
    const response = await axios.get('http://localhost:3002', {
      timeout: 5000
    });

    if (response.status === 200) {
      console.log(chalk.green('✓ Web platform is running'));
      console.log(chalk.cyan('  • URL: http://localhost:3002'));
      return true;
    }
  } catch (error: any) {
    if (error.code === 'ECONNREFUSED') {
      console.log(chalk.yellow('⚠ Web platform not running'));
      console.log(chalk.dim('  Start it with: cd ../upscaled-crosslist && npm run dev'));
    } else {
      console.log(chalk.red('✗ Connection error:'), error.message);
    }
    return false;
  }

  return false;
}

async function testDataSync() {
  console.log('\n🔍 Testing data sync...');

  try {
    // Get latest batch
    const latestBatch = await prisma.batch.findFirst({
      orderBy: { createdAt: 'desc' },
      include: {
        _count: {
          select: { products: true }
        }
      }
    });

    if (latestBatch) {
      console.log(chalk.green('✓ Data sync working'));
      console.log(chalk.cyan(`  • Latest batch: ${latestBatch.batchNumber}`));
      console.log(chalk.cyan(`  • Status: ${latestBatch.status}`));
      console.log(chalk.cyan(`  • Products: ${latestBatch._count.products}`));
      return true;
    } else {
      console.log(chalk.yellow('⚠ No batches found in database'));
      return false;
    }
  } catch (error: any) {
    console.log(chalk.red('✗ Data sync test failed:'), error.message);
    return false;
  }
}

async function main() {
  console.log(chalk.bold('\n╔════════════════════════════════════════╗'));
  console.log(chalk.bold('║  CLI ↔ Web Platform Integration Test  ║'));
  console.log(chalk.bold('╚════════════════════════════════════════╝'));

  const dbOk = await testDatabaseConnection();
  const webOk = await testWebPlatformConnection();
  const syncOk = await testDataSync();

  console.log('\n' + chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(chalk.bold('Test Results:'));
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));

  console.log(dbOk ? chalk.green('✓ Database') : chalk.red('✗ Database'));
  console.log(webOk ? chalk.green('✓ Web Platform') : chalk.yellow('⚠ Web Platform (optional)'));
  console.log(syncOk ? chalk.green('✓ Data Sync') : chalk.red('✗ Data Sync'));

  if (dbOk && syncOk) {
    console.log(chalk.green('\n✅ Integration is working!'));
    console.log(chalk.cyan('\nYou can now:'));
    console.log(chalk.dim('  • Run the CLI: npm run dev'));
    console.log(chalk.dim('  • View data: npx prisma studio'));
    console.log(chalk.dim('  • Use cross-listing features'));
  } else {
    console.log(chalk.red('\n❌ Integration has issues'));
    console.log(chalk.yellow('\nTroubleshooting:'));
    if (!dbOk) {
      console.log(chalk.dim('  • Check Docker: docker ps | grep upscaled-postgres'));
      console.log(chalk.dim('  • Start containers: cd ../upscaled-crosslist && docker-compose up -d'));
    }
    if (!syncOk) {
      console.log(chalk.dim('  • Run migration: cd ../upscaled-crosslist && npx tsx prisma/migration/csv-to-postgres.ts'));
    }
  }

  console.log('');
  await prisma.$disconnect();
}

main().catch(console.error);
