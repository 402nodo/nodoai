# 💳 402 Protocol

## Payment Required — Микроплатежи для API

---

## 🎯 Что такое 402?

**HTTP 402 Payment Required** — статус код, зарезервированный для будущего использования в микроплатежах. NODO реализует этот протокол для монетизации AI-анализа.

```
┌─────────────────────────────────────────────────────────┐
│  Traditional API                   NODO 402 API         │
│                                                         │
│  ❌ Monthly subscription           ✅ Pay per request   │
│  ❌ Pay for unused calls           ✅ Pay only for use  │
│  ❌ Complex billing                ✅ Instant settlement│
│  ❌ Minimum commitments            ✅ Start from $0.01  │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 How It Works

### Request Flow

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │         │   NODO   │         │ Payment  │
│          │         │  Server  │         │ Provider │
└────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                    │
     │  POST /analyze     │                    │
     │───────────────────>│                    │
     │                    │                    │
     │                    │  Check balance     │
     │                    │───────────────────>│
     │                    │<───────────────────│
     │                    │                    │
     │  402 Payment       │                    │
     │  Required          │                    │
     │<───────────────────│                    │
     │                    │                    │
     │  Payment           │                    │
     │───────────────────>│                    │
     │                    │  Verify            │
     │                    │───────────────────>│
     │                    │<───────────────────│
     │                    │                    │
     │  200 OK + Analysis │                    │
     │<───────────────────│                    │
     │                    │                    │
```

### 402 Response Format

```json
HTTP/1.1 402 Payment Required

{
  "error": {
    "code": "PAYMENT_REQUIRED",
    "message": "This request requires payment"
  },
  "payment": {
    "amount": "0.10",
    "currency": "USD",
    "description": "Deep AI Analysis (6 models)",
    "methods": [
      {
        "type": "lightning",
        "invoice": "lnbc100n1pj...",
        "expires_at": "2025-01-01T12:00:00Z"
      },
      {
        "type": "usdc",
        "address": "NoDo...xyz",
        "chain": "solana"
      },
      {
        "type": "stripe",
        "checkout_url": "https://checkout.stripe.com/..."
      }
    ]
  },
  "balance": {
    "current": "0.05",
    "required": "0.10"
  }
}
```

---

## 💰 Pricing Tiers

| Tier | Price | AI Models | Response Time | Use Case |
|------|-------|-----------|---------------|----------|
| **Quick** | $0.01 | 1 (fastest) | ~2s | Quick check |
| **Standard** | $0.05 | 3 models | ~5s | Normal use |
| **Deep** | $0.10 | 6 models | ~10s | Important decisions |

### Volume Discounts

| Monthly Volume | Discount |
|----------------|----------|
| $0 - $10 | 0% |
| $10 - $50 | 10% |
| $50 - $100 | 15% |
| $100+ | 20% |

### Subscription Option

| Plan | Price | Requests | Per Request |
|------|-------|----------|-------------|
| **Starter** | $10/mo | 150 standard | $0.067 |
| **Pro** | $50/mo | 1000 standard | $0.050 |
| **Unlimited** | $200/mo | Unlimited | - |

---

## ⚡ Payment Methods

### 1. Lightning Network (Recommended)

Мгновенные микроплатежи с минимальными комиссиями.

```javascript
// Client-side example
const invoice = response.payment.methods.find(m => m.type === 'lightning');

// Pay with any Lightning wallet
await wallet.payInvoice(invoice.invoice);

// Retry request with payment proof
const result = await fetch('/analyze', {
  headers: {
    'X-Payment-Preimage': preimage
  }
});
```

**Преимущества:**
- ⚡ Мгновенно (< 1 секунда)
- 💸 Комиссия < $0.001
- 🔒 Приватно
- 🌍 Глобально

### 2. USDC (Solana)

Стейблкоин платежи на Solana — быстро и дёшево.

```javascript
// Pay with USDC on Solana
const method = response.payment.methods.find(m => m.type === 'usdc');

// Using Solana web3.js
const transaction = new Transaction().add(
  createTransferInstruction(
    senderTokenAccount,
    method.address,
    wallet.publicKey,
    method.amount * 1e6  // USDC has 6 decimals
  )
);

const signature = await sendAndConfirmTransaction(connection, transaction, [wallet]);

// Include signature
const result = await fetch('/analyze', {
  headers: {
    'X-Payment-Signature': signature
  }
});
```

**Преимущества:**
- 💵 Stable value
- ⚡ Мгновенные транзакции (~400ms)
- 💸 Низкие комиссии (~$0.00025)
- 🌐 Работает с Phantom, Solflare, Backpack и др.

### 3. Stripe (Fiat)

Карты для тех, кто не в крипто.

```javascript
// Redirect to Stripe Checkout
window.location = response.payment.methods.find(m => m.type === 'stripe').checkout_url;

// After payment, user is redirected back with session_id
```

**Преимущества:**
- 💳 Привычные карты
- 🏦 Надёжно
- 📱 Apple/Google Pay

---

## 🔐 Account & Balance

### Prepaid Balance

Пользователи могут пополнить баланс заранее:

```
POST /api/account/topup

{
  "amount": 10.00,
  "method": "lightning"
}

Response:
{
  "invoice": "lnbc...",
  "balance_after": 10.00
}
```

### Check Balance

```
GET /api/account/balance

{
  "balance": 8.45,
  "currency": "USD",
  "requests_remaining": {
    "quick": 845,
    "standard": 169,
    "deep": 84
  }
}
```

---

## 🛠️ Implementation

### Middleware (FastAPI)

```python
from fastapi import Request, HTTPException

PRICING = {
    "quick": 0.01,
    "standard": 0.05,
    "deep": 0.10,
}

async def payment_middleware(request: Request, tier: str = "standard"):
    user_id = get_user_id(request)
    required = PRICING[tier]
    
    # Check prepaid balance
    balance = await get_balance(user_id)
    
    if balance >= required:
        # Deduct and proceed
        await deduct_balance(user_id, required)
        return True
    
    # Check for payment in headers
    payment_proof = request.headers.get("X-Payment-Preimage")
    if payment_proof:
        if await verify_lightning_payment(payment_proof, required):
            return True
    
    # Return 402
    raise HTTPException(
        status_code=402,
        detail={
            "error": {"code": "PAYMENT_REQUIRED"},
            "payment": generate_payment_options(required),
            "balance": {"current": balance, "required": required}
        }
    )
```

### Client SDK

```python
import nodo

client = nodo.Client(api_key="...")

# Auto-handles 402 with prepaid balance
result = client.analyze(
    market="polymarket.com/event/btc-150k",
    tier="deep"
)

# Or handle manually
try:
    result = client.analyze(...)
except nodo.PaymentRequired as e:
    print(f"Need to pay: {e.amount}")
    invoice = e.lightning_invoice
    # ... pay and retry
```

---

## 📊 Analytics

NODO предоставляет детальную аналитику расходов:

```
GET /api/account/usage

{
  "period": "2025-01",
  "total_spent": 45.30,
  "requests": {
    "quick": 120,
    "standard": 450,
    "deep": 89
  },
  "savings_from_volume": 4.53,
  "daily_breakdown": [
    {"date": "2025-01-01", "spent": 2.30, "requests": 28},
    ...
  ]
}
```

---

## 🔮 Future: L402 (Lightning HTTP 402)

NODO планирует полную поддержку [L402](https://docs.lightning.engineering/the-lightning-network/l402) — стандарта от Lightning Labs для HTTP 402.

```
WWW-Authenticate: L402 macaroon="...", invoice="lnbc..."
```

Это позволит:
- 🎫 Macaroons для делегирования доступа
- 🔄 Streaming payments
- 🤝 Interoperability с другими L402 сервисами

