# NODO x402 Python SDK

Python SDK for NODO x402 API - AI prediction market analysis with Solana micropayments.

## Installation

```bash
pip install nodo-x402

# With Solana support (for auto-payments)
pip install nodo-x402[solana]
```

## Quick Start

```python
from nodo_x402 import NodoClient

async def main():
    # Initialize with Solana keypair for auto-payments
    client = NodoClient(
        keypair_path="~/.config/solana/id.json"
    )
    
    # Analyze a market - auto-pays via x402
    result = await client.analyze(
        market="polymarket.com/event/btc-150k",
        tier="deep"  # $0.10
    )
    
    print(f"Consensus: {result.consensus}")
    print(f"Agreement: {result.agreement}")
    print(f"Confidence: {result.confidence}%")
    
    for model in result.models:
        print(f"  {model.name}: {model.action} ({model.confidence}%)")
    
    await client.close()

import asyncio
asyncio.run(main())
```

## API Methods

### AI Analysis

```python
# Multi-AI consensus analysis
result = await client.analyze(
    market="polymarket.com/event/...",
    tier="standard",  # quick ($0.01), standard ($0.05), deep ($0.10)
    strategy="yield_farming"  # yield_farming, delta_neutral, momentum
)
```

### Yield Scanner

```python
# Find high-probability opportunities
opportunities = await client.yield_scan(
    min_probability=0.95,
    min_volume=10000,
    max_days=30,
    risk_level="LOW"  # LOW, MEDIUM, HIGH
)

for opp in opportunities[:5]:
    print(f"{opp.question}: {opp.apy}% APY")
```

### Delta Scanner

```python
# Find logical mispricing
deltas = await client.delta_scan(
    min_profit=5.0,
    topic="BTC"
)

for d in deltas:
    print(f"[{d.topic}] {d.logic_error}")
    print(f"   Profit: {d.profit_potential}%")
```

### Market Data

```python
# Get markets
markets = await client.get_markets(
    platform="polymarket",
    min_volume=10000,
    search="bitcoin"
)

# Get single market
market = await client.get_market("btc-150k")
```

### Webhooks

```python
# Subscribe to alerts
webhook = await client.create_webhook(
    url="https://yoursite.com/webhook",
    events=["opportunity.yield", "opportunity.delta"]
)
```

## Manual Payment Mode

```python
from nodo_x402 import NodoClient, PaymentRequired

client = NodoClient(auto_pay=False)

try:
    result = await client.analyze(market="...")
except PaymentRequired as e:
    print(f"Payment required: ${e.amount}")
    print(f"Send to: {e.recipient}")
    print(f"Memo: {e.memo}")
    # Handle payment manually...
```

## License

MIT


