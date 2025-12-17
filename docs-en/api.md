# API Reference

NODO provides a REST API for programmatic access to market analysis.

---

## Base URL

```
https://api.nodo.ai/v1
```

For self-hosted instances, replace with your server URL.

---

## Authentication

All requests require an API key in the header:

```bash
Authorization: Bearer your_api_key
```

Get your API key from the Telegram bot using `/apikey` command.

---

## Endpoints

### POST /analyze

Analyze a prediction market using AI consensus.

**Request:**

```bash
curl -X POST https://api.nodo.ai/v1/analyze \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "market": "https://polymarket.com/event/btc-150k-2025",
    "tier": "standard",
    "strategy": "yield_farming"
  }'
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| market | string | Yes | Market URL or ID |
| tier | string | No | "quick", "standard", or "deep" (default: standard) |
| strategy | string | No | Analysis strategy to apply |

**Response (200 OK):**

```json
{
  "market": {
    "id": "btc-150k-2025",
    "question": "Will Bitcoin reach $150,000 by Dec 31, 2025?",
    "yes_price": 0.42,
    "no_price": 0.58,
    "volume": 1250000,
    "end_date": "2025-12-31T23:59:59Z"
  },
  "consensus": {
    "action": "SKIP",
    "confidence": 68,
    "agreement": 0.83,
    "reasoning": "Market is fairly priced given current BTC trajectory..."
  },
  "models": [
    {
      "name": "claude-3.5-sonnet",
      "action": "SKIP",
      "confidence": 72
    },
    {
      "name": "gpt-4o",
      "action": "SKIP",
      "confidence": 65
    }
  ],
  "dissent": [
    {
      "model": "deepseek",
      "action": "BUY_YES",
      "reasoning": "Historical Q4 rallies suggest higher probability..."
    }
  ],
  "meta": {
    "tier": "standard",
    "models_used": 3,
    "cost": 0.05,
    "latency_ms": 4200
  }
}
```

**Response (402 Payment Required):**

```json
{
  "error": {
    "code": "PAYMENT_REQUIRED",
    "message": "Insufficient balance"
  },
  "payment": {
    "amount": "0.05",
    "currency": "USD",
    "methods": [
      {
        "type": "lightning",
        "invoice": "lnbc50n1..."
      }
    ]
  }
}
```

---

### GET /markets

List available markets with optional filtering.

**Request:**

```bash
curl https://api.nodo.ai/v1/markets?limit=20&min_volume=10000 \
  -H "Authorization: Bearer your_api_key"
```

**Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| limit | int | Max markets to return (default: 50) |
| offset | int | Pagination offset |
| min_volume | float | Minimum volume in USD |
| topic | string | Filter by topic (BTC, ETH, POLITICS, etc.) |

**Response:**

```json
{
  "markets": [
    {
      "id": "btc-150k-2025",
      "question": "Will Bitcoin reach $150,000 by Dec 31, 2025?",
      "yes_price": 0.42,
      "no_price": 0.58,
      "volume": 1250000,
      "end_date": "2025-12-31T23:59:59Z",
      "url": "https://polymarket.com/event/btc-150k-2025"
    }
  ],
  "total": 342,
  "limit": 20,
  "offset": 0
}
```

---

### GET /opportunities

Get pre-scanned opportunities for a strategy.

**Request:**

```bash
curl https://api.nodo.ai/v1/opportunities?strategy=yield_farming&risk=moderate \
  -H "Authorization: Bearer your_api_key"
```

**Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| strategy | string | "yield_farming", "delta_neutral", "momentum" |
| risk | string | For yield: "safe", "moderate", "risky" |
| limit | int | Max opportunities (default: 10) |

**Response:**

```json
{
  "strategy": "yield_farming",
  "opportunities": [
    {
      "market_id": "christmas-2025",
      "question": "Will December 25, 2025 be Christmas Day?",
      "outcome": "YES",
      "price": 0.98,
      "profit_pct": 2.04,
      "apy": 24.8,
      "days_to_resolution": 30,
      "risk_level": "SAFE",
      "url": "https://polymarket.com/event/christmas-2025"
    }
  ],
  "scanned_at": "2024-12-17T10:30:00Z"
}
```

---

### GET /account/balance

Get your current prepaid balance.

**Request:**

```bash
curl https://api.nodo.ai/v1/account/balance \
  -H "Authorization: Bearer your_api_key"
```

**Response:**

```json
{
  "balance": "2.45",
  "currency": "USD",
  "requests_remaining": {
    "quick": 245,
    "standard": 49,
    "deep": 24
  }
}
```

---

### POST /account/topup

Generate a payment request to add funds.

**Request:**

```bash
curl -X POST https://api.nodo.ai/v1/account/topup \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5.00,
    "method": "lightning"
  }'
```

**Response:**

```json
{
  "amount": "5.00",
  "method": "lightning",
  "invoice": "lnbc5m1pj...",
  "expires_at": "2024-12-17T11:00:00Z"
}
```

---

### GET /account/usage

Get usage history.

**Request:**

```bash
curl "https://api.nodo.ai/v1/account/usage?days=7" \
  -H "Authorization: Bearer your_api_key"
```

**Response:**

```json
{
  "period": {
    "start": "2024-12-10",
    "end": "2024-12-17"
  },
  "total_requests": 47,
  "total_spent": "2.35",
  "by_tier": {
    "quick": 12,
    "standard": 30,
    "deep": 5
  },
  "daily": [
    {"date": "2024-12-17", "requests": 8, "spent": "0.40"},
    {"date": "2024-12-16", "requests": 12, "spent": "0.60"}
  ]
}
```

---

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| PAYMENT_REQUIRED | 402 | Insufficient balance |
| UNAUTHORIZED | 401 | Invalid or missing API key |
| RATE_LIMITED | 429 | Too many requests |
| MARKET_NOT_FOUND | 404 | Market URL/ID not found |
| INVALID_REQUEST | 400 | Malformed request |
| INTERNAL_ERROR | 500 | Server error |

**Error Response Format:**

```json
{
  "error": {
    "code": "MARKET_NOT_FOUND",
    "message": "Could not find market: xyz123",
    "details": {}
  }
}
```

---

## Rate Limits

| Tier | Requests/min | Burst |
|------|--------------|-------|
| Free | 10 | 20 |
| Paid | 60 | 100 |

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1702812345
```

---

## SDKs

### Python

```python
from nodo import NodoClient

client = NodoClient(api_key="your_key")

# Analyze a market
result = await client.analyze(
    market="polymarket.com/event/btc-150k",
    tier="standard"
)
print(f"Action: {result.consensus.action}")

# Get opportunities
opps = await client.opportunities(
    strategy="yield_farming",
    risk="moderate"
)
for opp in opps:
    print(f"{opp.question}: {opp.apy}% APY")
```

### JavaScript

```javascript
import { NodoClient } from '@nodo/sdk';

const client = new NodoClient({ apiKey: 'your_key' });

// Analyze a market
const result = await client.analyze({
  market: 'polymarket.com/event/btc-150k',
  tier: 'standard'
});
console.log(`Action: ${result.consensus.action}`);
```

### cURL

All examples in this documentation use cURL. Copy and run directly in terminal.

---

## Webhooks (Coming Soon)

Subscribe to alerts when opportunities match your criteria:

```json
{
  "event": "opportunity",
  "strategy": "yield_farming",
  "min_apy": 30,
  "risk_level": ["safe", "moderate"],
  "webhook_url": "https://your-server.com/webhook"
}
```

