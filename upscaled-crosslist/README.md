# Upscaled Cross-List Platform

Multi-marketplace inventory management system competing with Vendoo.

## Features

- Cross-list inventory across 10+ marketplaces
- AI-powered listing optimization (Claude + OpenAI)
- Auto-delist on sale detection
- Bulk operations (relist, delist, price updates)
- Advanced analytics dashboard
- Zero subscription costs

## Tech Stack

- **Frontend**: Next.js 14 + React 19 + Tailwind CSS
- **Backend**: Next.js API Routes
- **Database**: PostgreSQL 15 + Prisma ORM
- **Queue**: Bull + Redis
- **AI**: Claude API + Python OpenAI Agents service

## Prerequisites

- Node.js 18+ (with npm)
- Docker Desktop (for PostgreSQL + Redis)
- Python 3.10+ (for AI enrichment service)

## Quick Start

### 1. Start Database Services

```bash
# Start Docker Desktop first, then run:
docker-compose up -d

# Verify containers are running:
docker ps
```

### 2. Environment Variables

```bash
# Copy the example env file
cp .env.local.example .env.local

# Edit .env.local with your API credentials
```

### 3. Database Setup

```bash
# Install dependencies (already done)
npm install

# Initialize Prisma and push schema to database
npx prisma generate
npx prisma db push

# (Optional) Run migrations in the future
npm run db:migrate
```

### 4. Run Development Server

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### 5. Database Management

```bash
# Open Prisma Studio (visual database browser)
npm run db:studio
```

## Project Structure

```
upscaled-crosslist/
├── app/                    # Next.js App Router
│   ├── api/               # API routes
│   ├── dashboard/         # Dashboard pages
│   └── page.tsx           # Landing page
├── lib/                   # Utilities and core logic
│   ├── marketplaces/      # Marketplace adapters
│   ├── jobs/              # Background job processors
│   ├── ai/                # AI integration
│   └── db/                # Database utilities
├── components/            # React components
├── prisma/                # Database schema and migrations
│   ├── schema.prisma
│   └── seed.ts
└── python-ai-service/     # FastAPI microservice
```

## Supported Marketplaces

1. **eBay** (official API) ✅
2. **Shopify** (GraphQL API)
3. **Poshmark** (DSCO API)
4. **Mercari** (Puppeteer automation)
5. **Facebook Marketplace** (Meta partner API)
6. **Etsy** (REST API)
7. **Depop** (Selling API)
8. **Grailed** (Puppeteer automation)
9. **Vinted** (Puppeteer automation)
10. **Whatnot** (API TBD)

## Development Workflow

### Week 1: Foundation ✅
- [x] Create Next.js project
- [x] Setup PostgreSQL + Redis (Docker)
- [ ] Define Prisma schema
- [ ] Migrate CSV data to PostgreSQL
- [ ] Port eBay integration

### Weeks 2-6: Core Features
See implementation plan at `/Users/connorodea/.claude/plans/snug-greeting-cloud.md`

## Database Schema

**Core Tables:**
- `products` - Inventory items
- `marketplace_listings` - Cross-listing records
- `photos` - Product images
- `batches` - Batch processing tracker
- `sync_logs` - Audit trail
- `marketplace_configs` - API credentials

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run db:push` - Push Prisma schema to database
- `npm run db:migrate` - Run database migrations
- `npm run db:studio` - Open Prisma Studio
- `npm run db:seed` - Seed database with test data

## Migrating from Existing System

The existing `Upscaled_inv_processing` CLI (1,612 lines) will be migrated incrementally:

1. **Preserve**: SKU format, batch system, grade mappings
2. **Migrate**: CSV data → PostgreSQL
3. **Extend**: eBay integration → Multi-marketplace adapters
4. **Integrate**: Python AI service via FastAPI wrapper

## License

Private tool for Upscaled business operations.
