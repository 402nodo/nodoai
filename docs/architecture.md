# 🏗️ Архитектура

## System Overview

```
┌────────────────────────────────────────────────────────────────┐
│                         NODO PLATFORM                           │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│   │  Telegram   │    │   Web App   │    │  REST API   │       │
│   │    Bot      │    │  Dashboard  │    │   /v1/*     │       │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │
│          │                  │                   │               │
│          └──────────────────┼───────────────────┘               │
│                             │                                   │
│                             ▼                                   │
│   ┌─────────────────────────────────────────────────────┐     │
│   │                   API GATEWAY                        │     │
│   │  • Rate Limiting    • Auth    • 402 Payment Check   │     │
│   └─────────────────────────┬───────────────────────────┘     │
│                             │                                   │
│          ┌──────────────────┼──────────────────┐               │
│          ▼                  ▼                  ▼               │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│   │   Market    │    │  Analysis   │    │   Payment   │       │
│   │   Scanner   │    │   Engine    │    │   Service   │       │
│   └──────┬──────┘    └──────┬──────┘    └─────────────┘       │
│          │                  │                                   │
│          ▼                  ▼                                   │
│   ┌─────────────┐    ┌─────────────────────────────────┐      │
│   │ Polymarket  │    │        AI ORCHESTRATOR          │      │
│   │    API      │    │                                 │      │
│   └─────────────┘    │  ┌───────┐ ┌───────┐ ┌───────┐ │      │
│                      │  │Claude │ │ GPT-4 │ │Gemini │ │      │
│                      │  └───────┘ └───────┘ └───────┘ │      │
│                      │  ┌───────┐ ┌───────┐ ┌───────┐ │      │
│                      │  │ Llama │ │DeepSk │ │Mistral│ │      │
│                      │  └───────┘ └───────┘ └───────┘ │      │
│                      │                                 │      │
│                      │  ┌─────────────────────────┐   │      │
│                      │  │   CONSENSUS ENGINE      │   │      │
│                      │  └─────────────────────────┘   │      │
│                      └─────────────────────────────────┘      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 📦 Components

### 1. Market Scanner

Сканирует Polymarket и другие платформы в реальном времени.

```python
class MarketScanner:
    async def scan_yield_opportunities(min_prob: float) -> List[Opportunity]
    async def scan_delta_neutral() -> List[DeltaOpportunity]
    async def scan_momentum() -> List[MomentumSignal]
```

**Источники данных:**
- Polymarket Gamma API
- Kalshi API (planned)
- Azuro GraphQL (planned)

---

### 2. AI Orchestrator

Управляет запросами к нескольким AI моделям параллельно.

```python
class AIOrchestrator:
    models = [
        ClaudeClient(),      # Anthropic Claude Opus
        GPT4Client(),        # OpenAI GPT-4o
        GeminiClient(),      # Google Gemini Pro
        LlamaClient(),       # Meta Llama 405B
        DeepSeekClient(),    # DeepSeek
        MistralClient(),     # Mistral Large
    ]
    
    async def analyze(market: Market, strategy: Strategy) -> ConsensusResult:
        # 1. Send to all models in parallel
        tasks = [model.analyze(market) for model in self.models]
        results = await asyncio.gather(*tasks)
        
        # 2. Aggregate into consensus
        return self.consensus_engine.aggregate(results)
```

---

### 3. Consensus Engine

Агрегирует мнения AI моделей в единый вердикт.

```python
class ConsensusEngine:
    def aggregate(self, results: List[AIResult]) -> ConsensusResult:
        # Voting
        votes = {"BUY": 0, "HOLD": 0, "SKIP": 0}
        for r in results:
            votes[r.action] += r.confidence
        
        # Find majority
        consensus = max(votes, key=votes.get)
        agreement = votes[consensus] / sum(votes.values())
        
        # Find dissent
        dissent = [r for r in results if r.action != consensus]
        
        return ConsensusResult(
            action=consensus,
            agreement=agreement,
            confidence=avg([r.confidence for r in results]),
            dissent=dissent,
            details=[r.analysis for r in results]
        )
```

---

### 4. Payment Service (402)

Обрабатывает микроплатежи за запросы.

```python
class PaymentService:
    PRICING = {
        "quick": 0.01,      # $0.01 - 1 AI
        "standard": 0.05,   # $0.05 - 3 AI
        "deep": 0.10,       # $0.10 - 6 AI
    }
    
    async def check_payment(user_id: str, tier: str) -> bool:
        balance = await self.get_balance(user_id)
        return balance >= self.PRICING[tier]
    
    async def charge(user_id: str, tier: str) -> bool:
        amount = self.PRICING[tier]
        return await self.deduct_balance(user_id, amount)
```

**Поддерживаемые методы оплаты:**
- ⚡ Lightning Network (instant, low fees)
- 💵 USDC на Solana (instant, minimal fees)
- 💳 Stripe (fiat)

---

## 🔄 Request Flow

```
User                Gateway              Orchestrator           AI Models
  │                    │                      │                     │
  │  POST /analyze     │                      │                     │
  │───────────────────>│                      │                     │
  │                    │                      │                     │
  │                    │  Check Balance       │                     │
  │                    │─────────────────────>│                     │
  │                    │                      │                     │
  │                    │  OK / 402            │                     │
  │                    │<─────────────────────│                     │
  │                    │                      │                     │
  │  [If 402]          │                      │                     │
  │<───────────────────│                      │                     │
  │  Payment Required  │                      │                     │
  │                    │                      │                     │
  │  [If OK]           │                      │                     │
  │                    │  Analyze(market)     │                     │
  │                    │─────────────────────>│                     │
  │                    │                      │                     │
  │                    │                      │  Parallel Requests  │
  │                    │                      │────────────────────>│
  │                    │                      │<────────────────────│
  │                    │                      │                     │
  │                    │                      │  Consensus          │
  │                    │                      │─────────┐           │
  │                    │                      │<────────┘           │
  │                    │                      │                     │
  │                    │  Result              │                     │
  │                    │<─────────────────────│                     │
  │                    │                      │                     │
  │  Analysis Result   │                      │                     │
  │<───────────────────│                      │                     │
  │                    │                      │                     │
```

---

## 📁 File Structure

```
nodo/
├── bot/
│   ├── telegram_bot.py      # Telegram interface
│   ├── ai_analyzer.py       # Single AI (current)
│   ├── ai_orchestrator.py   # Multi-AI (new)
│   ├── consensus_engine.py  # Aggregation logic
│   ├── delta_scanner.py     # Delta neutral strategy
│   ├── yield_scanner.py     # Yield farming strategy
│   └── payment_service.py   # 402 Protocol handler
│
├── api/
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── analyze.py       # Analysis endpoints
│   │   ├── markets.py       # Market data
│   │   └── payments.py      # Payment handling
│   └── middleware/
│       └── payment_check.py # 402 middleware
│
├── web/
│   ├── index.html           # Landing page
│   └── dashboard/           # Web dashboard
│
├── docs/
│   ├── README.md
│   ├── concept.md
│   ├── architecture.md
│   └── ...
│
└── requirements.txt
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.12, FastAPI |
| **Bot** | python-telegram-bot |
| **AI APIs** | OpenRouter, Anthropic, OpenAI |
| **Database** | PostgreSQL + Redis |
| **Payments** | USDC on Solana, Lightning, Stripe |
| **Hosting** | Railway / Fly.io |

