<h1 align="center">NODO</h1>

<p align="center">
  <strong>Multi-AI Consensus for Prediction Markets</strong>
</p>

## 🧠 What is NODO?

NODO is an AI-powered analysis platform for prediction markets. Instead of relying on a single AI model, NODO queries **6 different models** simultaneously and aggregates their responses into a **consensus verdict**.

```
                     Market Data
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      ┌───────┐     ┌───────┐     ┌───────┐
      │Claude │     │ GPT-4 │     │Gemini │ ... (6 models)
      └───┬───┘     └───┬───┘     └───┬───┘
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                 Consensus Engine
                         │
                         ▼
              Final Analysis + Confidence
```

### Why Multi-AI Consensus?

| Single AI | Multi-AI Consensus |
|-----------|-------------------|
| Model bias affects results | Biases cancel out |
| Hallucinations go undetected | Detected by disagreement |
| Limited by training cutoff | Models complement each other |
| No validation | 5/6 agreement = high confidence |

---

## ✨ Features

### 🎯 Trading Strategies
- **Yield Farming** — Find high-probability events (95%+) for consistent returns
- **Delta Neutral** — Exploit price inconsistencies between related markets
- **Multi-Outcome Arbitrage** — Profit from mispriced multi-option markets
- **Momentum** — Track whale activity and price movements

### 🤖 AI Analysis
- 6 AI models analyze each opportunity
- Weighted consensus with confidence scores
- Dissent detection (when models disagree)
- Detailed reasoning from each model

### 💳 Pay-Per-Use (402 Protocol)
- No subscriptions — pay only for what you use
- Micropayments starting from $0.01
- USDC on Solana for instant settlement
- Prepaid balance system

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Telegram account
- OpenRouter API key (free tier available)

### Installation

```bash
# Clone repository
git clone https://github.com/nodo-ai/nodo.git
cd nodo

# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r bot/requirements.txt
```

### Configuration

```bash
# Copy example config
cp .env.example .env

# Edit with your values
nano .env
```

Required environment variables:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Run

```bash
python bot/telegram_bot.py
```

That's it! Open Telegram and start chatting with your bot.

---

## 📊 How It Works

### 1. Market Scanning

NODO continuously scans Polymarket for opportunities:

```python
# Example: Find yield farming opportunities
opportunities = await scanner.scan_yield_opportunities(
    min_probability=0.95,
    min_volume=10000
)
```

### 2. AI Analysis

Each opportunity is analyzed by multiple AI models:

```python
# Parallel analysis by 6 models
result = await orchestrator.analyze(
    market=opportunity,
    models=["claude-opus", "gpt-4o", "gemini-pro", ...]
)
```

### 3. Consensus Building

Responses are aggregated into a single verdict:

```json
{
  "consensus": "BUY",
  "agreement": "5/6 (83%)",
  "confidence": 82,
  "dissent": {
    "model": "gemini-pro",
    "reason": "Macro uncertainty..."
  }
}
```

### 4. User Notification

Results are delivered via Telegram or API:

```
🎯 NEW OPPORTUNITY

Market: "Will BTC reach $150K by Dec 2025?"
Action: BUY NO @ $0.92
Potential: 8.7% (45% APY)

AI Consensus: 5/6 agree
Confidence: 82%
```

---

## 🔌 API

### Base URL
```
https://api.nodo.ai/v1
```

### Analyze Market

```bash
curl -X POST https://api.nodo.ai/v1/analyze \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "market": "polymarket.com/event/btc-150k-2025",
    "tier": "deep"
  }'
```

### Response

```json
{
  "consensus": "BUY_NO",
  "agreement": "5/6",
  "confidence": 82,
  "models": [
    {"name": "claude-opus", "action": "BUY_NO", "confidence": 85},
    {"name": "gpt-4o", "action": "BUY_NO", "confidence": 80}
  ],
  "risks": ["Black swan events", "Market sentiment shifts"]
}
```

### Pricing

| Tier | Price | AI Models | Response Time |
|------|-------|-----------|---------------|
| Quick | $0.01 | 1 model | ~2s |
| Standard | $0.05 | 3 models | ~5s |
| Deep | $0.10 | 6 models | ~10s |

---

## 💰 Payments (Solana)

NODO uses USDC on Solana for micropayments:

- **Instant settlement** — transactions confirm in seconds
- **Low fees** — fraction of a cent per transaction
- **Familiar** — works with any Solana wallet (Phantom, Solflare, etc.)

```json
{
  "payment": {
    "amount": "0.10",
    "currency": "USDC",
    "chain": "solana",
    "address": "NoDo...xyz",
    "memo": "req_abc123"
  }
}
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Concept](docs/concept.md) | Core idea and vision |
| [Architecture](docs/architecture.md) | System design |
| [Strategies](docs/strategies.md) | Trading strategies explained |
| [API Reference](docs/api.md) | Full API documentation |
| [402 Protocol](docs/402-protocol.md) | Payment system |
| [Self-Hosting](docs-en/self-hosting.md) | Run your own instance |

### English Documentation

Full English documentation available in [`docs-en/`](docs-en/)

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastAPI |
| Bot | python-telegram-bot |
| AI | OpenRouter (Claude, GPT-4, Gemini, Llama) |
| Payments | USDC on Solana |
| Database | PostgreSQL, Redis |
| Hosting | Railway, Fly.io |

---

## 🗺️ Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| MVP | ✅ Done | Telegram bot with 2 strategies |
| Multi-AI | 🔄 In Progress | 6 model consensus |
| 402 Protocol | 📋 Planned | Solana micropayments |
| Web Dashboard | 📋 Planned | Full web interface |
| Public API | 📋 Planned | REST API for developers |

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/nodo.git

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and commit
git commit -m "Add amazing feature"

# Push and create PR
git push origin feature/amazing-feature
```

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- **Website**: [nodo.ai](https://nodo.ai)
- **Documentation**: [docs.nodo.ai](https://docs.nodo.ai)
- **Telegram Bot**: [@nodo_ai_bot](https://t.me/nodo_ai_bot)
- **Twitter**: [@nodo_ai](https://twitter.com/nodo_ai)

---

<p align="center">
  Built with 🧠 by the NODO team
</p>



