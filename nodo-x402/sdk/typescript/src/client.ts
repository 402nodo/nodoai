/**
 * NODO x402 Client
 * Handles API requests with automatic Solana USDC payments
 */

import {
  NodoClientOptions,
  AnalyzeOptions,
  AnalysisResult,
  YieldScanOptions,
  YieldOpportunity,
  DeltaScanOptions,
  DeltaOpportunity,
  Market,
  MarketsOptions,
  WebhookOptions,
  Webhook,
  UsageStats,
  PaymentInfo,
} from './types';
import { PaymentRequired, PaymentFailed, APIError } from './errors';
import { SolanaWallet } from './solana';

const DEFAULT_BASE_URL = 'https://api.nodo.ai/x402/v1';

export class NodoClient {
  private baseUrl: string;
  private autoPay: boolean;
  private wallet: SolanaWallet;

  /**
   * Create a new NODO client
   *
   * @example
   * ```typescript
   * import { NodoClient } from '@nodo-ai/x402';
   * import { Keypair } from '@solana/web3.js';
   *
   * const keypair = Keypair.fromSecretKey(yourSecretKey);
   * const client = new NodoClient({ keypair: keypair.secretKey });
   *
   * const result = await client.analyze({ market: 'polymarket.com/event/btc-150k' });
   * ```
   */
  constructor(options: NodoClientOptions = {}) {
    this.baseUrl = options.baseUrl || DEFAULT_BASE_URL;
    this.autoPay = options.autoPay !== false;
    this.wallet = new SolanaWallet({
      keypair: options.keypair,
      rpcUrl: options.rpcUrl,
    });
  }

  // ==================
  // AI Analysis
  // ==================

  /**
   * Analyze a prediction market using Multi-AI Consensus
   *
   * @param options - Analysis options
   * @returns Analysis result with consensus, models, and risks
   */
  async analyze(options: AnalyzeOptions): Promise<AnalysisResult> {
    const data = await this.request<AnalysisResult>('POST', '/analyze', {
      body: {
        market: options.market,
        tier: options.tier || 'standard',
        strategy: options.strategy || 'yield_farming',
      },
    });
    return this.transformAnalysisResult(data);
  }

  // ==================
  // Scanners
  // ==================

  /**
   * Scan for yield farming opportunities
   */
  async yieldScan(options: YieldScanOptions = {}): Promise<YieldOpportunity[]> {
    const params: Record<string, string | number> = {
      min_probability: options.minProbability || 0.95,
      min_volume: options.minVolume || 5000,
      max_days: options.maxDays || 30,
      limit: options.limit || 20,
    };
    if (options.riskLevel) {
      params.risk_level = options.riskLevel;
    }

    const data = await this.request<{ opportunities: unknown[] }>(
      'GET',
      '/yield/scan',
      { params }
    );
    return (data.opportunities || []).map(this.transformYieldOpportunity);
  }

  /**
   * Scan for delta neutral / mispricing opportunities
   */
  async deltaScan(options: DeltaScanOptions = {}): Promise<DeltaOpportunity[]> {
    const params: Record<string, string | number> = {
      min_profit: options.minProfit || 5.0,
      min_confidence: options.minConfidence || 50,
      limit: options.limit || 20,
    };
    if (options.topic) {
      params.topic = options.topic;
    }

    const data = await this.request<{ opportunities: unknown[] }>(
      'GET',
      '/delta/scan',
      { params }
    );
    return (data.opportunities || []).map(this.transformDeltaOpportunity);
  }

  /**
   * Scan for intra-platform arbitrage opportunities
   */
  async arbitrageScan(options: {
    minProfit?: number;
    minVolume?: number;
    limit?: number;
  } = {}): Promise<unknown[]> {
    const data = await this.request<{ opportunities: unknown[] }>(
      'GET',
      '/arbitrage/scan',
      {
        params: {
          min_profit: options.minProfit || 0.5,
          min_volume: options.minVolume || 1000,
          limit: options.limit || 20,
        },
      }
    );
    return data.opportunities || [];
  }

  /**
   * Smart category-specific analysis
   */
  async smartAnalyze(options: {
    question: string;
    currentPrice: number;
    outcome?: string;
    daysLeft?: number;
  }): Promise<unknown> {
    return this.request('POST', '/smart/analyze', {
      body: {
        question: options.question,
        current_price: options.currentPrice,
        outcome: options.outcome || 'YES',
        days_left: options.daysLeft || 30,
      },
    });
  }

  // ==================
  // Market Data
  // ==================

  /**
   * Get list of markets from prediction platforms
   */
  async getMarkets(options: MarketsOptions = {}): Promise<Market[]> {
    const params: Record<string, string | number | boolean> = {
      platform: options.platform || 'polymarket',
      active: options.active !== false,
      min_volume: options.minVolume || 0,
      limit: options.limit || 50,
    };
    if (options.search) {
      params.search = options.search;
    }

    const data = await this.request<{ markets: unknown[] }>('GET', '/markets', {
      params,
    });
    return (data.markets || []).map(this.transformMarket);
  }

  /**
   * Get detailed market info
   */
  async getMarket(
    marketId: string,
    platform = 'polymarket'
  ): Promise<Market | null> {
    const data = await this.request<{ market: unknown }>(
      'GET',
      `/markets/${marketId}`,
      { params: { platform } }
    );
    return data.market ? this.transformMarket(data.market) : null;
  }

  // ==================
  // Account
  // ==================

  /**
   * Get usage statistics
   */
  async getUsage(period?: string): Promise<UsageStats> {
    const params: Record<string, string> = {};
    if (period) params.period = period;
    return this.request('GET', '/account/usage', { params });
  }

  /**
   * Get current API pricing
   */
  async getPricing(): Promise<unknown> {
    return this.request('GET', '/account/pricing');
  }

  // ==================
  // Webhooks
  // ==================

  /**
   * Create a webhook subscription
   */
  async createWebhook(options: WebhookOptions): Promise<Webhook> {
    return this.request('POST', '/webhooks', {
      body: {
        url: options.url,
        events: options.events || ['opportunity.yield', 'opportunity.delta'],
        filters: options.filters,
      },
    });
  }

  /**
   * List your webhook subscriptions
   */
  async listWebhooks(): Promise<Webhook[]> {
    const data = await this.request<{ webhooks: Webhook[] }>('GET', '/webhooks');
    return data.webhooks || [];
  }

  /**
   * Delete a webhook subscription
   */
  async deleteWebhook(webhookId: string): Promise<void> {
    await this.request('DELETE', `/webhooks/${webhookId}`);
  }

  // ==================
  // Internal Methods
  // ==================

  private async request<T>(
    method: string,
    path: string,
    options: {
      params?: Record<string, string | number | boolean>;
      body?: unknown;
      headers?: Record<string, string>;
    } = {}
  ): Promise<T> {
    const url = new URL(path, this.baseUrl);

    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        url.searchParams.set(key, String(value));
      });
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.wallet.address) {
      headers['X-Wallet-Address'] = this.wallet.address;
    }

    let response = await fetch(url.toString(), {
      method,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    // Handle 402 Payment Required
    if (response.status === 402) {
      if (!this.autoPay) {
        const data = await response.json();
        const payment = data.payment as PaymentInfo;
        throw new PaymentRequired(
          parseFloat(payment.amount),
          payment.recipient,
          payment.memo
        );
      }

      // Auto-pay
      const paymentData = await response.json();
      const txSignature = await this.handlePayment(paymentData.payment);

      // Retry with payment proof
      headers['X-Payment-Tx'] = txSignature;
      response = await fetch(url.toString(), {
        method,
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });
    }

    if (!response.ok) {
      throw new APIError(response.status, await response.text());
    }

    return response.json();
  }

  private async handlePayment(payment: PaymentInfo): Promise<string> {
    try {
      const txSignature = await this.wallet.sendUsdc(
        payment.recipient,
        parseFloat(payment.amount),
        payment.memo
      );
      return txSignature;
    } catch (error) {
      throw new PaymentFailed(`Payment failed: ${error}`);
    }
  }

  // ==================
  // Transformers
  // ==================

  private transformAnalysisResult(data: unknown): AnalysisResult {
    const d = data as Record<string, unknown>;
    return d as AnalysisResult;
  }

  private transformYieldOpportunity(data: unknown): YieldOpportunity {
    const d = data as Record<string, unknown>;
    return {
      marketId: d.market_id as string,
      question: d.question as string,
      outcome: d.outcome as string,
      buyPrice: d.buy_price as number,
      profitPct: d.profit_pct as number,
      apy: d.apy as number,
      daysToResolution: d.days_to_resolution as number,
      volume: d.volume as number,
      riskLevel: d.risk_level as string,
      url: d.url as string,
    };
  }

  private transformDeltaOpportunity(data: unknown): DeltaOpportunity {
    const d = data as Record<string, unknown>;
    return {
      topic: d.topic as string,
      logicError: d.logic_error as string,
      profitPotential: d.profit_potential as number,
      confidence: d.confidence as number,
      action: d.action as string,
      explanation: d.explanation as string,
      eventA: this.transformDeltaMarket(d.event_a),
      eventB: this.transformDeltaMarket(d.event_b),
    };
  }

  private transformDeltaMarket(data: unknown): DeltaOpportunity['eventA'] {
    const d = data as Record<string, unknown>;
    return {
      question: d.question as string,
      yesPrice: d.yes_price as number,
      noPrice: d.no_price as number,
      url: d.url as string,
      threshold: d.threshold as number | undefined,
    };
  }

  private transformMarket(data: unknown): Market {
    const d = data as Record<string, unknown>;
    return {
      id: d.id as string,
      question: d.question as string,
      yesPrice: d.yes_price as number,
      noPrice: d.no_price as number,
      volume: d.volume as number,
      platform: d.platform as string,
      url: d.url as string,
      liquidity: d.liquidity as number | undefined,
      endDate: d.end_date as string | undefined,
      category: d.category as string | undefined,
    };
  }
}


