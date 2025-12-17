# Architecture

## System Overview

NODO consists of four main layers working together to deliver AI-powered market analysis.

```
┌─────────────────────────────────────────────┐
│              INTERFACE LAYER                 │
│     Telegram Bot  │  Web API  │  Dashboard  │
├─────────────────────────────────────────────┤
│              GATEWAY LAYER                   │
│   Auth  │  Rate Limiting  │  402 Payments   │
├─────────────────────────────────────────────┤
│              CORE SERVICES                   │
│  Scanner  │  AI Orchestrator  │  Consensus  │
├─────────────────────────────────────────────┤
│              DATA LAYER                      │
│   Polymarket API  │  AI Providers  │  Cache │
└─────────────────────────────────────────────┘
```

---

## Component 1: Market Scanner

The Scanner fetches and filters markets from Polymarket's API.

### What It Does

1. Queries Polymarket's Gamma API for active markets
2. Parses JSON response into structured objects
3. Filters by minimum volume, probability, and other criteria
4. Returns clean list of opportunities

### Why It Matters

Raw API data is messy. Prices come as strings, some fields are JSON-encoded within JSON, and many markets have zero liquidity. The Scanner normalizes everything.

### Code Example

```python
class MarketScanner:
    """Fetches and filters markets from Polymarket."""
    
    async def scan(self, min_volume: float = 5000) -> List[Market]:
        # Fetch raw data from Polymarket
        response = await self.client.get(
            "https://gamma-api.polymarket.com/markets",
            params={"limit": 500, "active": "true"}
        )
        
        # Parse and filter
        markets = []
        for raw in response.json():
            market = self._parse(raw)
            if market and market.volume >= min_volume:
                markets.append(market)
        
        return markets
```

Key detail: Polymarket returns `outcomePrices` as a JSON string inside JSON, so we need `json.loads()` to parse it:

```python
def _parse(self, raw: dict) -> Market:
    # API returns: {"outcomePrices": "[\"0.65\", \"0.35\"]"}
    prices = json.loads(raw.get("outcomePrices", "[]"))
    return Market(
        yes_price=float(prices[0]),
        no_price=float(prices[1]),
        ...
    )
```

---

## Component 2: AI Orchestrator

The Orchestrator sends market data to multiple AI models in parallel and collects their responses.

### What It Does

1. Builds a standardized prompt from market data
2. Sends prompt to all configured AI providers simultaneously
3. Waits for all responses (with timeout handling)
4. Parses each response into structured format

### Why Parallel Matters

Sequential calls to 6 models would take 30+ seconds. Parallel calls take only as long as the slowest model (~5-8 seconds).

### Code Example

```python
class AIOrchestrator:
    """Coordinates analysis across multiple AI models."""
    
    def __init__(self):
        self.providers = [
            OpenRouterProvider("anthropic/claude-3.5-sonnet"),
            OpenRouterProvider("openai/gpt-4o"),
            OpenRouterProvider("google/gemini-pro"),
            # ... more providers
        ]
    
    async def analyze(self, market: Market) -> List[AIResponse]:
        prompt = self._build_prompt(market)
        
        # Query ALL models in parallel
        tasks = [p.analyze(prompt) for p in self.providers]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed requests
        return [r for r in responses if isinstance(r, AIResponse)]
```

The prompt is structured to get consistent output from all models:

```python
def _build_prompt(self, market: Market) -> str:
    return f"""Analyze this prediction market:

Question: {market.question}
YES price: ${market.yes_price:.2f}
NO price: ${market.no_price:.2f}

Respond in this format:
ACTION: [BUY_YES / BUY_NO / SKIP]
CONFIDENCE: [1-100]
REASONING: [Your analysis]
RISKS: [List of risks]
"""
```

---

## Component 3: Consensus Engine

The Consensus Engine aggregates multiple AI responses into a single recommendation.

### What It Does

1. Collects all AI responses
2. Applies weights to each model's vote
3. Calculates agreement ratio
4. Adjusts confidence based on consensus level
5. Identifies and reports dissenting opinions

### Why Weights Matter

Not all models are equal. Claude excels at reasoning, GPT-4 at general knowledge, DeepSeek at math. Weights reflect this:

| Model | Weight | Why |
|-------|--------|-----|
| Claude 3.5 Sonnet | 1.5x | Best reasoning |
| GPT-4o | 1.2x | Broad knowledge |
| DeepSeek | 1.1x | Strong at math/logic |
| Others | 1.0x | Baseline |

### Code Example

```python
class ConsensusEngine:
    """Aggregates AI responses into weighted consensus."""
    
    def calculate(self, responses: List[AIResponse]) -> Consensus:
        # Weighted voting
        votes = {}
        for r in responses:
            weight = self.weights.get(r.model, 1.0)
            score = weight * r.confidence
            votes[r.action] = votes.get(r.action, 0) + score
        
        # Winner takes all
        winner = max(votes, key=votes.get)
        
        # Agreement ratio (how much consensus?)
        total = sum(votes.values())
        agreement = votes[winner] / total
        
        return Consensus(
            action=winner,
            agreement=agreement,
            confidence=self._calibrate(agreement, responses)
        )
```

Confidence calibration is key — high agreement boosts confidence, low agreement reduces it:

```python
def _calibrate(self, agreement: float, responses: list) -> int:
    raw_confidence = sum(r.confidence for r in responses) / len(responses)
    
    # Agreement multiplier
    if agreement > 0.9:      # Near unanimous
        multiplier = 1.2
    elif agreement > 0.7:    # Strong majority
        multiplier = 1.0
    elif agreement > 0.5:    # Simple majority
        multiplier = 0.8
    else:                    # Split decision
        multiplier = 0.5
    
    return int(raw_confidence * multiplier)
```

---

## Component 4: Payment Gateway

The Payment Gateway handles 402 micropayments.

### What It Does

1. Checks user's prepaid balance before processing
2. If sufficient, deducts and processes request
3. If insufficient, returns 402 with payment options
4. Verifies payments and credits balances

### Code Example

```python
class PaymentMiddleware:
    """Handles 402 Payment Required flow."""
    
    async def __call__(self, request, call_next):
        tier = request.json.get("tier", "standard")
        required = {"quick": 0.01, "standard": 0.05, "deep": 0.10}[tier]
        
        balance = await self.db.get_balance(request.user_id)
        
        if balance >= required:
            await self.db.deduct(request.user_id, required)
            return await call_next(request)
        
        # Insufficient balance - return 402
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment required",
                "amount": required,
                "methods": self._get_payment_options(required)
            }
        )
```

---

## Data Flow Summary

Here's how a request flows through the system:

```
1. User sends /analyze command via Telegram
          │
2. Bot extracts market URL, calls API
          │
3. Gateway checks auth, rate limits, payment
          │
4. Scanner fetches fresh market data
          │
5. Orchestrator sends to 6 AI models in parallel
          │
6. Consensus Engine aggregates responses
          │
7. Response formatted and sent back to user
```

Total latency: **5-10 seconds** (mostly waiting for AI models)
