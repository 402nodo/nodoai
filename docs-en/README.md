# NODO

**Multi-AI Consensus Engine for Prediction Markets**

NODO aggregates analysis from multiple AI models to provide validated insights for prediction market trading, monetized through the 402 Protocol.

---

## The Problem

Single AI models have limitations:
- **Biases** from training data
- **Hallucinations** (confident wrong answers)
- **Blind spots** on certain topics
- **No verification** of their claims

When trading real money on prediction markets, you need more than one opinion.

---

## The Solution

NODO queries **6 different AI models** in parallel, then aggregates their responses using weighted voting.

```
       Your Market Question
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 Claude    GPT-4    Gemini    ... (6 models)
    │         │         │
    └─────────┼─────────┘
              ▼
      Consensus Engine
              │
              ▼
    Validated Recommendation
       + Confidence Score
       + Dissent Analysis
```

**Why this works:**
- Different models make different mistakes → errors cancel out
- When models agree → higher confidence
- When they disagree → important warning signal

---

## Key Features

### 🤖 Multi-AI Consensus
6 frontier models analyze independently, then vote. Agreement level calibrates confidence.

### 💰 Pay-Per-Use (402 Protocol)
No subscriptions. Pay $0.01-$0.10 per analysis. Lightning Network, USDC, or prepaid balance.

### 📊 Multiple Strategies
- **Yield Farming** — Buy high-probability outcomes below $1
- **Delta Neutral** — Exploit logical mispricings between related markets
- **Momentum** — Detect breaking news from price movements

### ⚡ Real-Time Scanning
Continuous monitoring of Polymarket with instant Telegram alerts.

---

## Pricing

| Tier | Price | AI Models | Best For |
|------|-------|-----------|----------|
| Quick | $0.01 | 1 model | Fast screening |
| Standard | $0.05 | 3 models | Normal analysis |
| Deep | $0.10 | 6 models | Important decisions |

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/nodo-ai/nodo
cd nodo
pip install -r requirements.txt

# Configure
export TELEGRAM_BOT_TOKEN="your_token"
export OPENROUTER_API_KEY="your_key"

# Run
python bot/telegram_bot.py
```

See [Self-Hosting Guide](self-hosting.md) for detailed instructions.

---

## Documentation

| Section | Description |
|---------|-------------|
| [Concept & Vision](concept.md) | Why multi-AI consensus works |
| [Architecture](architecture.md) | System design and components |
| [AI Models](ai-models.md) | Model selection and voting |
| [402 Protocol](402-protocol.md) | Micropayment implementation |
| [Strategies](strategies.md) | Trading strategies explained |
| [API Reference](api.md) | REST API documentation |
| [Self-Hosting](self-hosting.md) | Deployment guide |

---

## How It Works (30 seconds)

1. **You submit** a market URL via Telegram or API
2. **Scanner fetches** fresh data from Polymarket
3. **Orchestrator sends** to 6 AI models in parallel
4. **Each model** analyzes and returns action + confidence
5. **Consensus engine** aggregates using weighted voting
6. **You receive** recommendation with confidence score and any dissenting opinions

Total time: **5-10 seconds**

---

## Example Output

```
📊 MARKET ANALYSIS

Question: Will Bitcoin reach $150K by Dec 2025?
Current: YES $0.42 | NO $0.58

🤖 CONSENSUS: SKIP
📈 Confidence: 68% (5/6 models agree)
📊 Agreement: 83%

💡 Reasoning: Market appears fairly priced given 
current trajectory. Risk/reward not favorable.

⚠️ DISSENT (1 model):
DeepSeek recommends BUY_YES — "Historical Q4 
rallies and ETF inflows suggest higher probability"
```

---

## Why 402 Protocol?

Traditional pricing models don't fit AI APIs:

| Model | Problem |
|-------|---------|
| Subscription | Pay $50/month, use 3 times |
| Rate limits | Hit limits when you need it most |
| Freemium | Hobbled features until you pay |

**402 Solution**: Pay exactly for what you use. $0.01 for quick scan, $0.10 for deep analysis. No waste.

---

## License

MIT
