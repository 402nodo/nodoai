# 🚀 NODO x402 - AI Prediction Market Analysis on Solana

[![x402 Protocol](https://img.shields.io/badge/x402-Solana-blueviolet)](https://solana.com/ru/x402/what-is-x402)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)

**Pay-per-request AI analysis for prediction markets using x402 protocol on Solana.**

> x402 enables HTTP 402 Payment Required on Solana with 400ms finality and $0.00025 fees.

## 🎯 What is NODO x402?

NODO x402 is an API service that provides AI-powered analysis of prediction markets (Polymarket, Kalshi, Azuro) with micropayments via Solana USDC.

```
┌─────────────────────────────────────────────────────────────────┐
│                         NODO x402 API                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   📊 Services                        💰 Pricing (USDC)          │
│   ─────────────────────────────────────────────────────────     │
│   🤖 AI Multi-Model Analysis         $0.01 - $0.10 / request    │
│   📈 Yield Farming Scanner           $0.005 / request           │
│   ⚖️  Delta Neutral Scanner          $0.01 / request            │
│   🧠 Smart Event Analyzer            $0.02 / request            │
│   🔀 Arbitrage Scanner               $0.01 / request            │
│   🌐 Cross-Platform Data             $0.001 / request           │
│   🔔 Real-time Webhooks              $0.005 / alert             │
│                                                                 │
│   ⚡ Powered by Solana x402 Protocol                            │
│   • 400ms finality                                              │
│   • $0.00025 transaction fees                                   │
│   • Native USDC support                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔥 Quick Start

### 1. Install SDK

```bash
# Python
pip install nodo-x402

# JavaScript/TypeScript
npm install @nodo-ai/x402
```

### 2. Get Your Solana Wallet

You need a Solana wallet with USDC for payments:
- [Phantom](https://phantom.app/)
- [Solflare](https://solflare.com/)
- [Backpack](https://backpack.app/)

### 3. Make Your First Request

```python
from nodo_x402 import NodoClient

# Initialize with your Solana keypair
client = NodoClient(
    keypair_path="~/.config/solana/id.json",  # or private key bytes
)

# Analyze a market - auto-pays via x402
result = await client.analyze(
    market="polymarket.com/event/btc-150k-2025",
    tier="deep"  # $0.10
)

print(f"Consensus: {result.consensus}")  # BUY_NO
print(f"Agreement: {result.agreement}")   # 5/6 models
print(f"Confidence: {result.confidence}%") # 82%
```

## 🔄 How x402 Works

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  Client  │       │   NODO   │       │  Solana  │
│          │       │  Server  │       │   USDC   │
└────┬─────┘       └────┬─────┘       └────┬─────┘
     │                  │                  │
     │  POST /analyze   │                  │
     │─────────────────>│                  │
     │                  │                  │
     │  402 Payment     │                  │
     │  Required        │                  │
     │<─────────────────│                  │
     │                  │                  │
     │  {amount: 0.10,  │                  │
     │   address: "...",│                  │
     │   memo: "req_123"│                  │
     │  }               │                  │
     │                  │                  │
     │  Sign & Send Tx  │                  │
     │─────────────────────────────────────>│
     │                  │                  │
     │  Tx Signature    │                  │
     │<─────────────────────────────────────│
     │                  │                  │
     │  Retry with      │                  │
     │  X-Payment-Sig   │                  │
     │─────────────────>│                  │
     │                  │  Verify Tx       │
     │                  │─────────────────>│
     │                  │<─────────────────│
     │                  │                  │
     │  200 OK          │                  │
     │  + Analysis      │                  │
     │<─────────────────│                  │
```

## 📡 API Endpoints

### Base URL
```
https://api.nodo.ai/x402/v1
```

### Available Endpoints

| Endpoint | Method | Description | Price |
|----------|--------|-------------|-------|
| `/analyze` | POST | AI multi-model consensus analysis | $0.01-$0.10 |
| `/yield/scan` | GET | Yield farming opportunities | $0.005 |
| `/delta/scan` | GET | Delta neutral mispricing | $0.01 |
| `/smart/analyze` | POST | Smart categorized analysis | $0.02 |
| `/arbitrage/scan` | GET | Cross-market arbitrage | $0.01 |
| `/markets` | GET | Market data (Polymarket/Kalshi) | $0.001 |
| `/webhooks` | POST | Subscribe to alerts | $0.005/alert |

### 402 Response Format

```json
HTTP/1.1 402 Payment Required

{
  "error": {
    "code": "PAYMENT_REQUIRED",
    "message": "This request requires payment"
  },
  "payment": {
    "x402_version": 1,
    "network": "solana-mainnet",
    "amount": "0.10",
    "currency": "USDC",
    "recipient": "NoDo...USDC",
    "memo": "req_abc123",
    "expires_at": "2025-12-19T12:00:00Z"
  }
}
```

### Success Response

```json
HTTP/1.1 200 OK

{
  "market": {
    "question": "Will Bitcoin reach $150,000 by Dec 31, 2025?",
    "yes_price": 0.08,
    "no_price": 0.92
  },
  "analysis": {
    "consensus": "BUY_NO",
    "agreement": "5/6",
    "confidence": 82,
    "apy": "45%"
  },
  "models": [
    {"name": "claude-opus", "action": "BUY_NO", "confidence": 85},
    {"name": "gpt-4o", "action": "BUY_NO", "confidence": 80},
    // ...
  ],
  "meta": {
    "request_id": "req_abc123",
    "cost": "$0.10",
    "network": "solana",
    "tx_signature": "5K..."
  }
}
```

## 💰 Pricing Tiers

### AI Analysis

| Tier | Price | AI Models | Response Time | Use Case |
|------|-------|-----------|---------------|----------|
| **Quick** | $0.01 | 1 (fastest) | ~2s | Quick check |
| **Standard** | $0.05 | 3 models | ~5s | Normal use |
| **Deep** | $0.10 | 6 models | ~10s | Important decisions |

### Scanner APIs

| API | Price | Description |
|-----|-------|-------------|
| Yield Scanner | $0.005 | High-probability events (95%+) |
| Delta Scanner | $0.01 | Logical mispricing opportunities |
| Arbitrage Scanner | $0.01 | Cross-outcome arbitrage |
| Smart Analyzer | $0.02 | Category-specific deep analysis |

### Volume Discounts

| Monthly Volume | Discount |
|----------------|----------|
| $0 - $10 | 0% |
| $10 - $50 | 10% |
| $50 - $100 | 15% |
| $100+ | 20% |

## 🛠️ SDK Examples

### Python

```python
from nodo_x402 import NodoClient

async def main():
    client = NodoClient(keypair_path="~/.config/solana/id.json")
    
    # 1. AI Analysis
    analysis = await client.analyze(
        market="polymarket.com/event/btc-150k",
        tier="deep"
    )
    print(f"Buy {analysis.consensus} - {analysis.confidence}% confidence")
    
    # 2. Yield Scanner
    opportunities = await client.yield_scan(
        min_probability=0.95,
        min_volume=10000
    )
    for opp in opportunities[:5]:
        print(f"{opp.question}: {opp.apy}% APY")
    
    # 3. Delta Scanner
    deltas = await client.delta_scan()
    for d in deltas[:3]:
        print(f"[{d.topic}] {d.logic_error}")
        print(f"   Profit: {d.profit_potential}%")
    
    # 4. Check balance/spending
    usage = await client.get_usage()
    print(f"Spent this month: ${usage.total_spent}")
    
    await client.close()

import asyncio
asyncio.run(main())
```

### TypeScript

```typescript
import { NodoClient } from '@nodo-ai/x402';
import { Keypair } from '@solana/web3.js';

async function main() {
  const keypair = Keypair.fromSecretKey(/* your key */);
  const client = new NodoClient({ keypair });
  
  // AI Analysis with auto-payment
  const result = await client.analyze({
    market: 'polymarket.com/event/btc-150k',
    tier: 'deep'
  });
  
  console.log(`Consensus: ${result.consensus}`);
  console.log(`Agreement: ${result.agreement}`);
  
  // Yield opportunities
  const yields = await client.yieldScan({ minProbability: 0.95 });
  
  for (const opp of yields.slice(0, 5)) {
    console.log(`${opp.question}: ${opp.apy}% APY`);
  }
}

main();
```

## 🔧 Self-Hosting

You can run your own NODO x402 server:

```bash
# Clone repository
git clone https://github.com/nodo-ai/nodo-x402
cd nodo-x402

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

```bash
# Solana
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_USDC_MINT=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
NODO_WALLET_ADDRESS=NoDo...
NODO_PRIVATE_KEY=...

# AI APIs
OPENROUTER_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Server
DEBUG=false
LOG_LEVEL=INFO
```

## 🌐 Supported Platforms

NODO x402 aggregates data from multiple prediction markets:

| Platform | Status | Data Available |
|----------|--------|----------------|
| Polymarket | ✅ Live | Full market data, prices, volume |
| Kalshi | ✅ Live | Market data, orderbook |
| Azuro | 🔄 Beta | Sports betting markets |
| PredictIt | 📋 Planned | Political markets |

## 🤖 AI Models Used

| Model | Provider | Use Case |
|-------|----------|----------|
| Claude Opus | Anthropic | Deep reasoning |
| GPT-4o | OpenAI | General analysis |
| Gemini Pro | Google | Data synthesis |
| Llama 405B | Meta | Alternative view |
| DeepSeek | DeepSeek | Financial analysis |
| Mistral Large | Mistral | European perspective |

## 📊 Why x402 on Solana?

| Feature | x402 Solana | Traditional API |
|---------|-------------|-----------------|
| Payment | Pay per request | Monthly subscription |
| Finality | 400ms | Days (invoices) |
| Fees | $0.00025 | $0.30+ (Stripe) |
| Minimum | $0.001 | $10+ |
| AI Agent Ready | ✅ | ❌ |
| Global | ✅ | Card restrictions |

## 🔐 Security

- All payments verified on-chain
- No custody of user funds
- Stateless authentication via signatures
- Rate limiting per wallet
- Audit logs for all transactions

## 📈 Roadmap

- [x] Core x402 payment flow
- [x] Multi-AI consensus
- [x] Yield/Delta scanners
- [ ] Streaming payments for webhooks
- [ ] L402 macaroon support
- [ ] Cross-chain (Base, Polygon)
- [ ] AI Agent marketplace

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🔗 Links

- [Website](https://nodo.ai)
- [Documentation](https://docs.nodo.ai)
- [x402 Protocol](https://solana.com/ru/x402/what-is-x402)
- [Discord](https://discord.gg/nodo)
- [Twitter](https://twitter.com/nodo_ai)

---

**Built with ❤️ for the AI Agent Economy on Solana**


