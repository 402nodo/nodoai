/**
 * NODO x402 TypeScript SDK Example
 * Demonstrates AI analysis with automatic Solana USDC payments.
 */

import { NodoClient, PaymentRequired } from '../sdk/typescript/src';

async function main() {
  console.log('='.repeat(60));
  console.log('  NODO x402 - AI Prediction Market Analysis');
  console.log('  Powered by Solana Micropayments');
  console.log('='.repeat(60));
  console.log();

  // Initialize client
  // For production with auto-payment:
  // const keypair = Keypair.fromSecretKey(yourSecretKey);
  // const client = new NodoClient({ keypair: keypair.secretKey });

  // For this example, manual payment mode
  const client = new NodoClient({
    baseUrl: 'http://localhost:8000',
    autoPay: false,
  });

  try {
    // ==================
    // 1. AI Analysis
    // ==================
    console.log('[1] AI Multi-Model Analysis');
    console.log('-'.repeat(40));

    try {
      const result = await client.analyze({
        market: 'polymarket.com/event/btc-150k-2025',
        tier: 'deep',
      });

      console.log(`Market: ${result.market.question}`);
      console.log(`Consensus: ${result.analysis.consensus}`);
      console.log(`Agreement: ${result.analysis.agreement}`);
      console.log(`Confidence: ${result.analysis.confidence}%`);
      console.log();

      console.log('Model Votes:');
      for (const model of result.models) {
        console.log(`  • ${model.name}: ${model.action} (${model.confidence}%)`);
      }

      if (result.dissent) {
        console.log(`\nDissent: ${result.dissent.model} says ${result.dissent.action}`);
      }

      console.log(`\nCost: ${result.meta.cost}`);
    } catch (error) {
      if (error instanceof PaymentRequired) {
        console.log(`💳 Payment Required: $${error.amount} USDC`);
        console.log(`   Recipient: ${error.recipient}`);
        console.log(`   Memo: ${error.memo}`);
      } else {
        throw error;
      }
    }

    console.log();

    // ==================
    // 2. Yield Scanner
    // ==================
    console.log('[2] Yield Farming Scanner');
    console.log('-'.repeat(40));

    try {
      const opportunities = await client.yieldScan({
        minProbability: 0.95,
        minVolume: 10000,
        riskLevel: 'LOW',
        limit: 5,
      });

      console.log(`Found ${opportunities.length} opportunities:`);
      opportunities.forEach((opp, i) => {
        console.log(`\n${i + 1}. ${opp.question}`);
        console.log(`   Buy ${opp.outcome} @ $${opp.buyPrice.toFixed(3)}`);
        console.log(`   Profit: ${opp.profitPct.toFixed(2)}% | APY: ${opp.apy.toFixed(0)}%`);
        console.log(`   Days: ${opp.daysToResolution} | Risk: ${opp.riskLevel}`);
      });
    } catch (error) {
      if (error instanceof PaymentRequired) {
        console.log(`💳 Payment Required: $${error.amount} USDC`);
      } else {
        throw error;
      }
    }

    console.log();

    // ==================
    // 3. Delta Scanner
    // ==================
    console.log('[3] Delta Neutral Scanner (Mispricing)');
    console.log('-'.repeat(40));

    try {
      const deltas = await client.deltaScan({
        minProfit: 5.0,
        topic: 'BTC',
        limit: 3,
      });

      console.log(`Found ${deltas.length} mispricing opportunities:`);
      deltas.forEach((d, i) => {
        console.log(`\n${i + 1}. [${d.topic}] ${d.logicError}`);
        console.log(`   Profit Potential: ${d.profitPotential.toFixed(1)}%`);
        console.log(`   Confidence: ${d.confidence}%`);
        console.log(`   Action: ${d.action}`);
      });
    } catch (error) {
      if (error instanceof PaymentRequired) {
        console.log(`💳 Payment Required: $${error.amount} USDC`);
      } else {
        throw error;
      }
    }

    console.log();

    // ==================
    // 4. Market Data
    // ==================
    console.log('[4] Market Data');
    console.log('-'.repeat(40));

    try {
      const markets = await client.getMarkets({
        platform: 'polymarket',
        minVolume: 100000,
        search: 'bitcoin',
        limit: 3,
      });

      console.log(`Found ${markets.length} markets:`);
      markets.forEach((m) => {
        console.log(`\n• ${m.question}`);
        console.log(`  YES: $${m.yesPrice.toFixed(2)} | NO: $${m.noPrice.toFixed(2)}`);
        console.log(`  Volume: $${m.volume.toLocaleString()}`);
      });
    } catch (error) {
      if (error instanceof PaymentRequired) {
        console.log(`💳 Payment Required: $${error.amount} USDC`);
      } else {
        throw error;
      }
    }

    console.log();

    // ==================
    // 5. Pricing Info
    // ==================
    console.log('[5] API Pricing');
    console.log('-'.repeat(40));

    const pricing = (await client.getPricing()) as {
      pricing: {
        ai_analysis: Record<string, { price: number; models: number }>;
        scanners: Record<string, number>;
      };
    };

    console.log('AI Analysis:');
    for (const [tier, info] of Object.entries(pricing.pricing.ai_analysis)) {
      console.log(`  • ${tier}: $${info.price} (${info.models} models)`);
    }

    console.log('\nScanners:');
    for (const [scanner, price] of Object.entries(pricing.pricing.scanners)) {
      console.log(`  • ${scanner}: $${price}`);
    }
  } finally {
    // Client cleanup would go here if needed
  }

  console.log();
  console.log('='.repeat(60));
  console.log('  Demo complete! Check https://nodo.ai for more info');
  console.log('='.repeat(60));
}

main().catch(console.error);


