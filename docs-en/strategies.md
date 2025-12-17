# Trading Strategies

NODO supports multiple prediction market strategies. Each has different risk/reward profiles and requires different analysis.

---

## Strategy 1: Yield Farming

### The Concept

Buy shares in events that are almost certain to happen, but are priced slightly below $1.00.

### Real Example

**Market**: "Will December 25, 2025 be Christmas Day?"
- YES price: $0.98
- This event is 100% certain (it's a calendar fact)

**The Trade**:
- Buy 100 YES shares @ $0.98 = $98 investment
- When market resolves YES, receive $100
- Profit: $2 (2.04% return)

**Why This Works**: Market makers and liquidity providers need small spreads to operate. Even "obvious" events don't trade at exactly $1.00.

### Risk Levels

| Level | Min Probability | Expected APY | Risk |
|-------|-----------------|--------------|------|
| SAFE | 97%+ | 10-30% | Very low |
| MODERATE | 95%+ | 30-50% | Low |
| RISKY | 90%+ | 50-100% | Medium |

### Calculating APY

If you earn 2% in 30 days, the annualized return is:

```
APY = (profit_percent / days) × 365
APY = (2% / 30) × 365 = 24.3%
```

### Code Implementation

```python
def find_yield_opportunities(markets: list, min_prob: float = 0.95):
    """Find high-probability outcomes trading below $1."""
    
    opportunities = []
    
    for market in markets:
        # Check if YES or NO has high probability
        if market.yes_price >= min_prob:
            outcome = "YES"
            price = market.yes_price
        elif market.no_price >= min_prob:
            outcome = "NO"  
            price = market.no_price
        else:
            continue
        
        # Calculate returns
        profit_pct = ((1.0 - price) / price) * 100
        days = days_until_resolution(market.end_date)
        apy = (profit_pct / days) * 365 if days > 0 else 0
        
        opportunities.append({
            "market": market.question,
            "outcome": outcome,
            "price": price,
            "profit": profit_pct,
            "apy": apy
        })
    
    return sorted(opportunities, key=lambda x: x["apy"], reverse=True)
```

### AI Enhancement

AI models evaluate whether the event is truly as certain as the price suggests:

- **Legitimate 98%**: "Will the sun rise tomorrow?" → Safe
- **False 98%**: "Will [politician] win?" → Historical upsets happen
- **Edge cases**: "Will Christmas be Dec 25?" → Yes, but what if market meant "observed holiday"?

---

## Strategy 2: Delta Neutral

### The Concept

Find logical inconsistencies between related markets and exploit them.

### Real Example

Two markets on Polymarket:
- "Bitcoin reaches $100K by 2025" - YES @ $0.45
- "Bitcoin reaches $150K by 2025" - YES @ $0.50

**The Problem**: This is logically impossible. If BTC reaches $150K, it MUST have passed $100K first. So P(150K) cannot be greater than P(100K).

**The Trade**:
- The $100K YES is underpriced at $0.45
- It should be worth at least $0.50 (the $150K price)
- Buy $100K YES, wait for market to correct

### Types of Inconsistencies

**1. Reach Thresholds**
- Higher price target should have LOWER YES price
- "Reach $150K" YES ≤ "Reach $100K" YES

**2. Dip Thresholds**
- Lower dip target should have LOWER YES price
- "Dip to $50K" YES ≤ "Dip to $70K" YES

**3. Subset Events**
- Specific outcome should have LOWER price than general
- "Win Pennsylvania" YES ≤ "Win Election" YES

**4. Direct Arbitrage**
- YES + NO should equal $1.00
- If YES + NO < $0.98, buy both for guaranteed profit

### Code Implementation

```python
def find_threshold_mispricing(markets: list, topic: str = "BTC"):
    """Find mispriced threshold markets."""
    
    # Filter to reach-type markets about the topic
    reach_markets = [
        m for m in markets 
        if topic in m.question.upper() 
        and any(word in m.question.lower() for word in ["reach", "hit", "above"])
    ]
    
    # Extract threshold from each
    for m in reach_markets:
        m.threshold = extract_price_threshold(m.question)
    
    # Sort by threshold
    reach_markets.sort(key=lambda x: x.threshold)
    
    # Check adjacent pairs
    opportunities = []
    for i in range(len(reach_markets) - 1):
        lower = reach_markets[i]      # e.g., BTC $100K
        higher = reach_markets[i+1]   # e.g., BTC $150K
        
        # Mispricing if higher threshold has higher YES price
        if higher.yes_price > lower.yes_price:
            opportunities.append({
                "error": f"${higher.threshold:,.0f} YES > ${lower.threshold:,.0f} YES",
                "buy": f"${lower.threshold:,.0f} YES",
                "expected_value": higher.yes_price,
                "current_price": lower.yes_price,
                "profit_potential": (higher.yes_price - lower.yes_price) / lower.yes_price * 100
            })
    
    return opportunities
```

### AI Enhancement

AI models verify the logical relationship:

- **Confirm connection**: Are these markets about the same underlying event?
- **Check timeframes**: "BTC $100K by Dec" vs "BTC $100K by June" are NOT comparable
- **Spot exceptions**: "BTC touches $100K" vs "BTC closes above $100K" have different meanings

---

## Strategy 3: Momentum

### The Concept

Detect significant price movements that may indicate breaking news or trend formation.

### Why It Works

Prediction markets react to news, but not instantly:
1. News breaks
2. Informed traders move first
3. Price starts moving
4. More traders notice
5. Price continues moving

If you detect the movement early, you can ride the trend.

### Signal Types

**Surge**: >10% price move in 24 hours
- Usually indicates breaking news
- Check news sources before acting

**Volume Spike**: 3x normal volume
- Large players are moving
- May precede price movement

**Trend**: Consistent direction over 3+ days
- Sustained movement suggests real information
- Not just noise

### Code Implementation

```python
def detect_momentum(market: Market, price_history: list) -> Signal:
    """Detect momentum signals in market."""
    
    current = market.yes_price
    price_24h_ago = get_price_at(price_history, hours=24)
    
    if price_24h_ago is None:
        return None
    
    change = (current - price_24h_ago) / price_24h_ago
    
    # Surge detection
    if abs(change) > 0.10:  # >10% move
        return Signal(
            type="SURGE",
            direction="UP" if change > 0 else "DOWN",
            magnitude=abs(change) * 100,
            action="Investigate news, consider following trend"
        )
    
    return None
```

### AI Enhancement

AI models analyze why the momentum is happening:

- **News search**: What triggered the movement?
- **Sustainability**: Is this a one-time reaction or ongoing trend?
- **Overreaction**: Has the market moved too far too fast?

---

## Strategy Comparison

| Strategy | Complexity | Capital Needed | Expected Return | Time Commitment |
|----------|------------|----------------|-----------------|-----------------|
| Yield Farming | Low | Medium | 20-50% APY | Low (set & forget) |
| Delta Neutral | Medium | Low | Variable | Medium (monitoring) |
| Momentum | High | High | Variable | High (active trading) |

### When to Use Each

**Yield Farming**: Best for passive income. Set up positions, wait for resolution. Works well with AI to validate "obvious" events.

**Delta Neutral**: Best when markets are new or illiquid. Mispricings are more common. Requires understanding of logical relationships.

**Momentum**: Best for active traders with news feeds. Requires quick execution and risk management.

---

## AI-Powered Strategy Selection

When a user submits a market for analysis, NODO can recommend which strategy applies:

```python
def recommend_strategy(market: Market, ai_consensus: Consensus) -> str:
    """Recommend best strategy for this market."""
    
    # High probability + near-term = Yield Farming
    if max(market.yes_price, market.no_price) > 0.90:
        if market.days_to_resolution < 60:
            return "YIELD_FARMING"
    
    # Related markets exist = check Delta Neutral
    related = find_related_markets(market)
    if related:
        inconsistencies = check_logical_consistency(market, related)
        if inconsistencies:
            return "DELTA_NEUTRAL"
    
    # Recent price movement = Momentum
    if abs(market.price_change_24h) > 0.05:
        return "MOMENTUM"
    
    # Default
    return "STANDARD_ANALYSIS"
```
