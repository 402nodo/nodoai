# 📡 API Reference

## Base URL

```
https://api.nodo.ai/v1
```

---

## Authentication

All requests require an API key:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.nodo.ai/v1/analyze
```

Get your API key at [nodo.ai/dashboard](https://nodo.ai/dashboard)

---

## Endpoints

### POST /analyze

Analyze a prediction market with Multi-AI Consensus.

**Request:**
```json
{
  "market": "polymarket.com/event/btc-150k-2025",
  "strategy": "yield_farming",  // yield_farming | delta_neutral | momentum
  "tier": "deep"                // quick ($0.01) | standard ($0.05) | deep ($0.10)
}
```

**Response (200):**
```json
{
  "market": {
    "question": "Will Bitcoin reach $150,000 by Dec 31, 2025?",
    "yes_price": 0.08,
    "no_price": 0.92,
    "volume": 1250000,
    "end_date": "2025-12-31"
  },
  "analysis": {
    "consensus": "BUY_NO",
    "agreement": "5/6",
    "confidence": 82,
    "action": "Buy NO at $0.92",
    "potential_profit": "8.7%",
    "apy": "45%"
  },
  "models": [
    {
      "name": "claude-opus",
      "action": "BUY_NO",
      "confidence": 85,
      "reasoning": "BTC would need 50% growth in 14 days..."
    },
    // ... other models
  ],
  "dissent": {
    "model": "gemini-pro",
    "action": "HOLD",
    "reason": "Macro uncertainty..."
  },
  "risks": [
    "Black swan events could cause rapid price movement",
    "Market sentiment can shift quickly"
  ],
  "meta": {
    "request_id": "req_abc123",
    "cost": "$0.10",
    "processing_time": "8.2s"
  }
}
```

**Response (402 - Payment Required):**
```json
{
  "error": {
    "code": "PAYMENT_REQUIRED",
    "message": "Insufficient balance"
  },
  "payment": {
    "amount": "0.10",
    "currency": "USD",
    "methods": [
      {"type": "lightning", "invoice": "lnbc..."},
      {"type": "usdc", "address": "NoDo...xyz", "chain": "solana"}
    ]
  },
  "balance": {
    "current": "0.03",
    "required": "0.10"
  }
}
```

---

### GET /markets

List available markets.

**Query params:**
- `strategy` - Filter by strategy (yield_farming, delta_neutral)
- `min_volume` - Minimum volume ($)
- `min_probability` - Minimum probability (0-1)
- `limit` - Max results (default 20)

**Response:**
```json
{
  "markets": [
    {
      "id": "abc123",
      "question": "Will BTC reach $150K?",
      "yes_price": 0.08,
      "no_price": 0.92,
      "volume": 1250000,
      "url": "polymarket.com/event/...",
      "strategy_fit": {
        "yield_farming": {"score": 95, "action": "BUY_NO"},
        "delta_neutral": {"score": 0}
      }
    }
  ],
  "total": 156
}
```

---

### GET /opportunities

Get pre-scanned opportunities.

**Query params:**
- `strategy` - Required (yield_farming, delta_neutral, momentum)
- `risk_level` - safe | moderate | risky
- `limit` - Max results

**Response:**
```json
{
  "opportunities": [
    {
      "type": "yield_farming",
      "market": {...},
      "action": "BUY_NO",
      "profit_potential": "3.2%",
      "apy": "85%",
      "risk_level": "safe",
      "days_to_resolution": 14,
      "quick_analysis": "High probability event..."
    }
  ]
}
```

---

### GET /account/balance

Check account balance.

**Response:**
```json
{
  "balance": "15.45",
  "currency": "USD",
  "requests_available": {
    "quick": 1545,
    "standard": 309,
    "deep": 154
  }
}
```

---

### POST /account/topup

Add funds to account.

**Request:**
```json
{
  "amount": 10.00,
  "method": "lightning"  // lightning | usdc | stripe
}
```

**Response:**
```json
{
  "invoice": "lnbc100n1...",  // for lightning
  "expires_at": "2025-01-01T12:30:00Z",
  "balance_after": "25.45"
}
```

---

### GET /account/usage

Get usage statistics.

**Query params:**
- `period` - Month (YYYY-MM)

**Response:**
```json
{
  "period": "2025-01",
  "total_spent": 45.30,
  "total_requests": 659,
  "by_tier": {
    "quick": {"count": 120, "spent": 1.20},
    "standard": {"count": 450, "spent": 22.50},
    "deep": {"count": 89, "spent": 8.90}
  },
  "by_strategy": {
    "yield_farming": 450,
    "delta_neutral": 150,
    "momentum": 59
  }
}
```

---

## Rate Limits

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 10 | 100 |
| Paid | 60 | 10,000 |
| Enterprise | Custom | Custom |

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `PAYMENT_REQUIRED` | 402 | Need payment |
| `INVALID_MARKET` | 400 | Market not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## SDKs

### Python
```python
pip install nodo-ai

from nodo import Client

client = Client(api_key="...")
result = client.analyze("polymarket.com/event/...", tier="deep")
print(result.consensus)
```

### JavaScript
```javascript
npm install @nodo-ai/sdk

import { Nodo } from '@nodo-ai/sdk';

const nodo = new Nodo({ apiKey: '...' });
const result = await nodo.analyze('polymarket.com/event/...', { tier: 'deep' });
console.log(result.consensus);
```

---

## Webhooks

Subscribe to events:

```json
POST /webhooks
{
  "url": "https://yoursite.com/webhook",
  "events": ["opportunity.new", "market.resolved"]
}
```

Event payload:
```json
{
  "event": "opportunity.new",
  "data": {
    "strategy": "yield_farming",
    "market": {...},
    "potential": "5.2%"
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

