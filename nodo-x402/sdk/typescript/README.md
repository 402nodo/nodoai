# @nodo-ai/x402

TypeScript SDK for NODO x402 API - AI prediction market analysis with Solana micropayments.

## Installation

```bash
npm install @nodo-ai/x402
# or
yarn add @nodo-ai/x402
# or
pnpm add @nodo-ai/x402
```

## Quick Start

```typescript
import { NodoClient } from '@nodo-ai/x402';
import { Keypair } from '@solana/web3.js';

async function main() {
  // Load your Solana keypair
  const keypair = Keypair.fromSecretKey(yourSecretKey);

  // Initialize client with auto-payment
  const client = new NodoClient({
    keypair: keypair.secretKey,
  });

  // Analyze a market - auto-pays via x402
  const result = await client.analyze({
    market: 'polymarket.com/event/btc-150k',
    tier: 'deep', // $0.10
  });

  console.log(`Consensus: ${result.analysis.consensus}`);
  console.log(`Agreement: ${result.analysis.agreement}`);
  console.log(`Confidence: ${result.analysis.confidence}%`);

  for (const model of result.models) {
    console.log(`  ${model.name}: ${model.action} (${model.confidence}%)`);
  }
}

main();
```

## API Methods

### AI Analysis

```typescript
const result = await client.analyze({
  market: 'polymarket.com/event/...',
  tier: 'standard', // 'quick' ($0.01), 'standard' ($0.05), 'deep' ($0.10)
  strategy: 'yield_farming', // 'yield_farming', 'delta_neutral', 'momentum'
});
```

### Yield Scanner

```typescript
const opportunities = await client.yieldScan({
  minProbability: 0.95,
  minVolume: 10000,
  maxDays: 30,
  riskLevel: 'LOW', // 'LOW', 'MEDIUM', 'HIGH'
});

for (const opp of opportunities) {
  console.log(`${opp.question}: ${opp.apy}% APY`);
}
```

### Delta Scanner

```typescript
const deltas = await client.deltaScan({
  minProfit: 5.0,
  topic: 'BTC',
});

for (const d of deltas) {
  console.log(`[${d.topic}] ${d.logicError}`);
  console.log(`   Profit: ${d.profitPotential}%`);
}
```

### Market Data

```typescript
// Get markets
const markets = await client.getMarkets({
  platform: 'polymarket',
  minVolume: 10000,
  search: 'bitcoin',
});

// Get single market
const market = await client.getMarket('btc-150k');
```

### Webhooks

```typescript
// Subscribe to alerts
const webhook = await client.createWebhook({
  url: 'https://yoursite.com/webhook',
  events: ['opportunity.yield', 'opportunity.delta'],
});

// List webhooks
const webhooks = await client.listWebhooks();

// Delete webhook
await client.deleteWebhook(webhook.id);
```

## Manual Payment Mode

```typescript
import { NodoClient, PaymentRequired } from '@nodo-ai/x402';

const client = new NodoClient({ autoPay: false });

try {
  const result = await client.analyze({ market: '...' });
} catch (error) {
  if (error instanceof PaymentRequired) {
    console.log(`Payment required: $${error.amount}`);
    console.log(`Send to: ${error.recipient}`);
    console.log(`Memo: ${error.memo}`);
    // Handle payment manually...
  }
}
```

## Types

Full TypeScript support with exported types:

```typescript
import type {
  AnalysisResult,
  YieldOpportunity,
  DeltaOpportunity,
  Market,
  Webhook,
} from '@nodo-ai/x402';
```

## License

MIT


