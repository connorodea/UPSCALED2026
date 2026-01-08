import fs from 'fs/promises';
import path from 'path';
import { spawn } from 'child_process';
import axios from 'axios';

export interface ManifestSummary {
  row_count?: number;
  msrp_total?: number;
  avg_msrp?: number | null;
  msrp_column?: string | null;
  quantity_column?: string | null;
  description_column?: string | null;
  brand_column?: string | null;
  category_column?: string | null;
  top_brands?: Array<{ name: string; count: number }>;
  top_categories?: Array<{ name: string; count: number }>;
  sample_items?: Array<{ description?: string; msrp?: number | null; quantity?: number }>;
}

export interface WatchlistItem {
  auction_id?: string;
  url?: string;
  title?: string;
  current_bid_value?: number;
  lot_price_value?: number;
  msrp_value?: number;
  retail_value_value?: number;
  items_count_value?: number;
  condition?: string;
  warehouse?: string;
  auction_end?: string;
  manifest_url?: string;
  manifest_path?: string | null;
  manifest_summary?: ManifestSummary | null;
}

export interface WatchlistPayload {
  fetched_at: string;
  source_url?: string | null;
  items: WatchlistItem[];
}

export type Decision = 'PASS' | 'FAIL';

export interface ProfitabilityResult {
  auctionId: string;
  title?: string;
  decision: Decision;
  ruleDecision: Decision;
  aiDecision?: Decision;
  aiConfidence?: string;
  aiSummary?: string;
  estimatedResaleValue?: number;
  estimatedProfit?: number;
  estimatedMargin?: number;
  costBasis?: number;
  msrpTotal?: number;
}

interface LlmDecisionPayload {
  decision?: string;
  confidence?: string;
  rationale?: string;
  comps?: string;
  risks?: string;
}

export class TechLiquidatorsIntegration {
  private dataDir = path.join(process.cwd(), 'data', 'techliquidators');
  private watchlistPath = path.join(this.dataDir, 'watchlist.json');
  private analysisPath = path.join(this.dataDir, 'analysis.json');

  async syncWatchlist(): Promise<WatchlistPayload | null> {
    const root = await this.findProjectRoot(process.cwd());
    if (!root) {
      throw new Error('Project root not found. Run from the UPSCALED workspace.');
    }

    await fs.mkdir(this.dataDir, { recursive: true });

    const scriptPath = path.join(
      root,
      '08_AUTOMATION',
      'CLI_Tools',
      'auction_scraper',
      'sync_techliquidators_watchlist.py'
    );
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

    const args = [scriptPath, '--out-dir', this.dataDir];
    const cookieFile = process.env.TECHLIQUIDATORS_COOKIE_FILE;
    const cookieHeader = process.env.TECHLIQUIDATORS_COOKIE;
    const watchlistUrl = process.env.TECHLIQUIDATORS_WATCHLIST_URL;
    const maxItems = process.env.TECHLIQUIDATORS_MAX_ITEMS;
    const force = process.env.TECHLIQUIDATORS_FORCE_MANIFESTS;

    if (cookieFile) {
      args.push('--cookie-file', cookieFile);
    }
    if (cookieHeader) {
      args.push('--cookie-header', cookieHeader);
    }
    if (watchlistUrl) {
      args.push('--watchlist-url', watchlistUrl);
    }
    if (maxItems) {
      args.push('--max-items', maxItems);
    }
    if (force && (force === '1' || force.toLowerCase() === 'true')) {
      args.push('--force');
    }

    await new Promise<void>((resolve, reject) => {
      const child = spawn(pythonCmd, args, { stdio: 'inherit' });
      child.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error('TechLiquidators watchlist sync failed'));
        }
      });
    });

    return this.readWatchlist();
  }

  async analyzeWatchlist(): Promise<ProfitabilityResult[]> {
    await fs.mkdir(this.dataDir, { recursive: true });
    const payload = await this.readWatchlist();
    if (!payload) {
      return [];
    }

    const results: ProfitabilityResult[] = [];
    for (const item of payload.items) {
      results.push(await this.analyzeItem(item));
    }

    await fs.writeFile(this.analysisPath, JSON.stringify(results, null, 2));
    return results;
  }

  private async analyzeItem(item: WatchlistItem): Promise<ProfitabilityResult> {
    const auctionId = item.auction_id || 'unknown';
    const msrpTotal = item.manifest_summary?.msrp_total ?? item.msrp_value ?? 0;
    const costBasis = this.getCostBasis(item);
    const estimatedResaleValue = msrpTotal ? msrpTotal * 0.5 : 0;
    const estimatedProfit = estimatedResaleValue - (costBasis || 0);
    const estimatedMargin = costBasis ? estimatedProfit / costBasis : 0;

    const minMargin = this.getMinMargin();
    const ruleDecision: Decision =
      costBasis && estimatedResaleValue > 0 && estimatedMargin >= minMargin ? 'PASS' : 'FAIL';

    let aiDecision: Decision | undefined;
    let aiConfidence: string | undefined;
    let aiSummary: string | undefined;

    const llm = await this.requestLlmDecision(item, {
      costBasis,
      msrpTotal,
      estimatedResaleValue,
      estimatedProfit,
      estimatedMargin,
    });

    if (llm) {
      aiDecision = llm.decision === 'PASS' ? 'PASS' : 'FAIL';
      aiConfidence = llm.confidence;
      aiSummary = [llm.rationale, llm.comps, llm.risks].filter(Boolean).join(' ');
    }

    const decision: Decision = aiDecision || ruleDecision;

    return {
      auctionId,
      title: item.title,
      decision,
      ruleDecision,
      aiDecision,
      aiConfidence,
      aiSummary,
      estimatedResaleValue: this.roundMoney(estimatedResaleValue),
      estimatedProfit: this.roundMoney(estimatedProfit),
      estimatedMargin: this.roundPercent(estimatedMargin),
      costBasis: this.roundMoney(costBasis || 0),
      msrpTotal: this.roundMoney(msrpTotal),
    };
  }

  private getCostBasis(item: WatchlistItem): number | null {
    if (item.current_bid_value && item.current_bid_value > 0) {
      return item.current_bid_value;
    }
    if (item.lot_price_value && item.lot_price_value > 0) {
      return item.lot_price_value;
    }
    return null;
  }

  private getMinMargin(): number {
    const raw = process.env.TECHLIQUIDATORS_MIN_MARGIN;
    if (!raw) {
      return 0.2;
    }
    const value = Number.parseFloat(raw);
    return Number.isFinite(value) ? value : 0.2;
  }

  private roundMoney(value: number): number {
    return Math.round(value * 100) / 100;
  }

  private roundPercent(value: number): number {
    return Math.round(value * 1000) / 1000;
  }

  private async requestLlmDecision(
    item: WatchlistItem,
    metrics: {
      costBasis: number | null;
      msrpTotal: number;
      estimatedResaleValue: number;
      estimatedProfit: number;
      estimatedMargin: number;
    }
  ): Promise<LlmDecisionPayload | null> {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return null;
    }

    const model = process.env.OPENAI_MODEL || 'gpt-5.2';
    const prompt = [
      'You are a liquidation analyst.',
      'Decide PASS or FAIL based on profitability and resale risk.',
      'Use general market knowledge only; no live browsing.',
      'Base resale value on 50% of MSRP unless data suggests otherwise.',
      'Return JSON with keys: decision, confidence, rationale, comps, risks.',
      '',
      `Listing: ${item.title || ''}`,
      `Auction ID: ${item.auction_id || ''}`,
      `Current Bid: ${metrics.costBasis ?? 'unknown'}`,
      `MSRP Total: ${metrics.msrpTotal || 0}`,
      `Estimated Resale (50% MSRP): ${metrics.estimatedResaleValue || 0}`,
      `Estimated Profit: ${metrics.estimatedProfit || 0}`,
      `Estimated Margin: ${metrics.estimatedMargin || 0}`,
      `Condition: ${item.condition || ''}`,
      `Warehouse: ${item.warehouse || ''}`,
      `Manifest Summary: ${JSON.stringify(item.manifest_summary || {})}`,
    ].join('\n');

    try {
      const response = await axios.post(
        'https://api.openai.com/v1/chat/completions',
        {
          model,
          temperature: 0.2,
          messages: [
            { role: 'system', content: 'Respond with JSON only.' },
            { role: 'user', content: prompt },
          ],
        },
        {
          headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          timeout: 20000,
        }
      );

      const content = response.data?.choices?.[0]?.message?.content;
      if (!content) {
        return null;
      }
      return this.extractJson(content);
    } catch {
      return null;
    }
  }

  private extractJson(text: string): LlmDecisionPayload | null {
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start === -1 || end === -1 || end <= start) {
      return null;
    }
    try {
      return JSON.parse(text.slice(start, end + 1));
    } catch {
      return null;
    }
  }

  private async readWatchlist(): Promise<WatchlistPayload | null> {
    try {
      const raw = await fs.readFile(this.watchlistPath, 'utf-8');
      return JSON.parse(raw) as WatchlistPayload;
    } catch {
      return null;
    }
  }

  private async findProjectRoot(start: string): Promise<string | null> {
    let current = path.resolve(start);
    while (true) {
      const candidate = path.join(current, '01_SOURCING');
      try {
        const stat = await fs.stat(candidate);
        if (stat.isDirectory()) {
          return current;
        }
      } catch {
        // continue upward
      }
      const parent = path.dirname(current);
      if (parent === current) {
        break;
      }
      current = parent;
    }
    return null;
  }
}
