#!/bin/bash
#
# CLI Integration Setup Script
# Automatically configures the CLI to work with the web platform
#

set -e

echo "🔗 Setting up CLI ↔ Web Platform Integration..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Install dependencies
echo "📦 Step 1: Installing dependencies..."
npm install --save @prisma/client axios
npm install --save-dev prisma

echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# Step 2: Link Prisma schema
echo "🔗 Step 2: Linking to shared Prisma schema..."

# Remove existing prisma directory if it exists
if [ -d "prisma" ]; then
  echo -e "${YELLOW}⚠${NC} Existing prisma directory found, backing up..."
  mv prisma prisma.backup.$(date +%s)
fi

# Create symbolic link to web platform's Prisma schema
ln -sf ../upscaled-crosslist/prisma ./prisma

echo -e "${GREEN}✓${NC} Prisma schema linked"
echo ""

# Step 3: Generate Prisma client
echo "⚙️  Step 3: Generating Prisma client..."
npx prisma generate

echo -e "${GREEN}✓${NC} Prisma client generated"
echo ""

# Step 4: Setup environment variables
echo "🔧 Step 4: Setting up environment variables..."

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${GREEN}✓${NC} .env file created (please edit with your credentials)"
else
  echo -e "${YELLOW}⚠${NC} .env file already exists, skipping"
fi

echo ""

# Step 5: Test database connection
echo "🔍 Step 5: Testing database connection..."

if docker ps | grep -q upscaled-postgres; then
  echo -e "${GREEN}✓${NC} PostgreSQL container is running"

  # Test connection
  if docker exec upscaled-postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Database connection successful"
  else
    echo -e "${YELLOW}⚠${NC} Database not responding, check Docker"
  fi
else
  echo -e "${YELLOW}⚠${NC} PostgreSQL container not running"
  echo "   Start it with: cd ../upscaled-crosslist && docker-compose up -d"
fi

echo ""

# Step 6: Update package.json scripts
echo "📝 Step 6: Adding helper scripts to package.json..."

# Check if scripts already exist
if grep -q '"db:generate"' package.json; then
  echo -e "${YELLOW}⚠${NC} Scripts already exist in package.json"
else
  echo "   You should manually add these scripts to package.json:"
  echo '   "db:generate": "npx prisma generate"'
  echo '   "db:studio": "npx prisma studio"'
fi

echo ""

# Done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Integration setup complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your database credentials"
echo "  2. Test CLI: npm run dev"
echo "  3. Read INTEGRATION_GUIDE.md for full documentation"
echo ""
echo "Quick test:"
echo "  npx prisma studio  # Open database browser"
echo ""
