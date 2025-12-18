/**
 * NODO x402 SDK Types
 */

export interface NodoClientOptions {
  /** Solana keypair for auto-payments */
  keypair?: Uint8Array;
  /** API base URL */
  baseUrl?: string;
  /** Automatically handle 402 payments */
  autoPay?: boolean;
  /** Solana RPC URL */
  rpcUrl?: string;
}

export interface AnalyzeOptions {
  /** Market URL or ID */
  market: string;
  /** Analysis tier: quick ($0.01), standard ($0.05), deep ($0.10) */
  tier?: 'quick' | 'standard' | 'deep';
  /** Analysis strategy */
  strategy?: 'yield_farming' | 'delta_neutral' | 'momentum';
}

export interface AIModelResult {
  name: string;
  action: string;
  confidence: number;
  reasoning?: string;
}

export interface Dissent {
  model: string;
  action: string;
  reason: string;
}

export interface AnalysisResult {
  market: {
    question: string;
    yesPrice: number;
    noPrice: number;
    volume?: number;
    endDate?: string;
    url: string;
  };
  analysis: {
    consensus: string;
    agreement: string;
    confidence: number;
    action: string;
    potentialProfit?: string;
    apy?: string;
  };
  models: AIModelResult[];
  dissent?: Dissent;
  risks: string[];
  meta: {
    requestId: string;
    cost: string;
    processingTime: string;
    modelsUsed: number;
    tier: string;
  };
}

export interface YieldScanOptions {
  minProbability?: number;
  minVolume?: number;
  maxDays?: number;
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH';
  limit?: number;
}

export interface YieldOpportunity {
  marketId: string;
  question: string;
  outcome: string;
  buyPrice: number;
  profitPct: number;
  apy: number;
  daysToResolution: number;
  volume: number;
  riskLevel: string;
  url: string;
}

export interface DeltaScanOptions {
  minProfit?: number;
  minConfidence?: number;
  topic?: string;
  limit?: number;
}

export interface DeltaMarket {
  question: string;
  yesPrice: number;
  noPrice: number;
  url: string;
  threshold?: number;
}

export interface DeltaOpportunity {
  topic: string;
  logicError: string;
  profitPotential: number;
  confidence: number;
  action: string;
  explanation: string;
  eventA: DeltaMarket;
  eventB: DeltaMarket;
}

export interface Market {
  id: string;
  question: string;
  yesPrice: number;
  noPrice: number;
  volume: number;
  platform: string;
  url: string;
  liquidity?: number;
  endDate?: string;
  category?: string;
}

export interface MarketsOptions {
  platform?: 'polymarket' | 'kalshi';
  active?: boolean;
  minVolume?: number;
  search?: string;
  limit?: number;
}

export interface WebhookOptions {
  url: string;
  events?: string[];
  filters?: Record<string, unknown>;
}

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  filters?: Record<string, unknown>;
  status: string;
  createdAt: string;
}

export interface PaymentInfo {
  x402Version: number;
  network: string;
  amount: string;
  currency: string;
  recipient: string;
  memo: string;
  expiresAt: string;
}

export interface UsageStats {
  period: string;
  totalSpent: number;
  totalRequests: number;
  byEndpoint: Record<string, { count: number; spent: number }>;
  byTier?: Record<string, { count: number; spent: number }>;
}


