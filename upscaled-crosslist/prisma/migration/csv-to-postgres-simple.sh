#!/bin/bash
#
# Simple CSV to PostgreSQL migration using psql
# This bypasses Prisma and directly inserts data using SQL
#

set -e

CSV_FILE="../Upscaled_inv_processing/data/inventory.csv"
BATCH_STATE="../Upscaled_inv_processing/data/batch-state.json"

echo "🚀 Starting CSV to PostgreSQL migration (SQL-based)..."

# Read CSV and create SQL INSERT statements
docker exec -i upscaled-postgres psql -U postgres -d upscaled_crosslist <<'EOSQL'

-- First, create batches
INSERT INTO batches (id, batch_number, location, total_items, processed_items, status, created_at)
VALUES
  (gen_random_uuid(), 'B1', 'DEN001', 50, 50, 'completed', NOW()),
  (gen_random_uuid(), 'B2', 'DEN001', 49, 49, 'active', NOW())
ON CONFLICT (batch_number) DO NOTHING;

EOSQL

echo "✓ Created batches"
echo "✓ Ready to import products"
echo ""
echo "Note: For full CSV import, we'll need to parse the CSV file."
echo "The database schema is ready. You can now manually import or use the web interface."
