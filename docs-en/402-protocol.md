# 402 Protocol Implementation

## What is HTTP 402?

HTTP status code 402 was reserved in 1999 for "Payment Required" but was never officially standardized. The original HTTP spec authors knew that someday, micropayments on the internet would be important.

25 years later, with Lightning Network and stablecoins, micropayments are finally practical. NODO implements 402 for pay-per-request API access.

---

## The Traditional Problem

### Subscription Model Issues

| Problem | Impact |
|---------|--------|
| Pay $50/month, use 3 times | 94% waste |
| Need analysis NOW, no subscription | Can't access |
| Usage spikes during events | Hit rate limits |
| Multiple tiers | Complex pricing decisions |

### The 402 Solution

Pay exactly for what you use. No subscription, no minimums, no rate limits (just cost).

---

## How It Works

### Flow Diagram

```
1. Client sends request
        │
        ▼
2. Server checks: Does user have balance?
        │
    ┌───┴───┐
    │       │
   Yes      No
    │       │
    ▼       ▼
3a. Deduct  3b. Return 402
    balance     + payment options
    │       
    ▼       
4. Process request
    │
    ▼
5. Return result
```

### Request Without Balance

When a client makes a request without sufficient balance, they receive:

```json
{
  "error": {
    "code": "PAYMENT_REQUIRED",
    "message": "This request requires $0.05"
  },
  "payment": {
    "amount": "0.05",
    "currency": "USD",
    "tier": "standard",
    "methods": [
      {
        "type": "lightning",
        "invoice": "lnbc50n1p...",
        "expires_in": 600
      },
      {
        "type": "usdc",
        "chain": "polygon",
        "address": "0x...",
        "amount": "0.05"
      }
    ]
  },
  "balance": {
    "current": "0.02",
    "required": "0.05",
    "shortfall": "0.03"
  }
}
```

The client can then:
1. Pay the Lightning invoice
2. Send USDC to the address
3. Top up their prepaid balance

---

## Server Implementation

### Middleware Approach

The payment check happens in middleware, before the request handler:

```python
class PaymentMiddleware:
    """Check payment before processing requests."""
    
    PRICES = {
        "quick": 0.01,      # 1 AI model
        "standard": 0.05,   # 3 AI models
        "deep": 0.10        # 6 AI models
    }
    
    async def __call__(self, request, call_next):
        # Skip payment for non-paid endpoints
        if not request.url.path.startswith("/api/analyze"):
            return await call_next(request)
        
        # Get required amount
        tier = request.json.get("tier", "standard")
        required = self.PRICES[tier]
        
        # Check balance
        user_id = request.state.user_id
        balance = await self.db.get_balance(user_id)
        
        if balance >= required:
            # Has balance - deduct and process
            await self.db.deduct(user_id, required)
            return await call_next(request)
        
        # No balance - return 402
        return self.create_402_response(required, balance)
```

### Creating Payment Options

Each payment method requires different setup:

```python
def create_payment_options(self, amount: float) -> list:
    """Generate payment options for 402 response."""
    options = []
    
    # Lightning invoice
    if self.lightning_enabled:
        sats = int(amount * 100000)  # USD to sats (approximate)
        invoice = self.lightning.create_invoice(
            amount_sats=sats,
            memo=f"NODO API - ${amount}",
            expiry=600  # 10 minutes
        )
        options.append({
            "type": "lightning",
            "invoice": invoice.payment_request,
            "amount_sats": sats,
            "expires_in": 600
        })
    
    # USDC on Polygon
    options.append({
        "type": "usdc",
        "chain": "polygon",
        "chain_id": 137,
        "address": self.usdc_address,
        "amount": str(amount)
    })
    
    return options
```

---

## Payment Verification

### Lightning Payments

Lightning payments include a "preimage" as proof of payment. The client includes this in subsequent requests:

```python
async def verify_lightning_payment(self, preimage: str, expected: float):
    """Verify Lightning payment using preimage."""
    
    # Hash the preimage to get payment hash
    payment_hash = sha256(bytes.fromhex(preimage)).hexdigest()
    
    # Look up the invoice
    invoice = await self.lightning.lookup_invoice(payment_hash)
    
    if not invoice.settled:
        return {"verified": False, "error": "Invoice not paid"}
    
    if invoice.amount_sats < int(expected * 100000):
        return {"verified": False, "error": "Insufficient amount"}
    
    return {"verified": True, "amount": invoice.amount_sats}
```

### USDC Payments

For USDC, we watch the blockchain for incoming transfers:

```python
async def verify_usdc_payment(self, tx_hash: str, expected: float):
    """Verify USDC transfer on-chain."""
    
    # Get transaction receipt
    receipt = await self.web3.eth.get_transaction_receipt(tx_hash)
    
    if not receipt or receipt.status != 1:
        return {"verified": False, "error": "Transaction failed"}
    
    # Parse Transfer event
    transfers = self.usdc_contract.events.Transfer().process_receipt(receipt)
    
    for transfer in transfers:
        if transfer.args.to.lower() == self.address.lower():
            amount = transfer.args.value / 1e6  # USDC has 6 decimals
            if amount >= expected:
                return {"verified": True, "amount": amount}
    
    return {"verified": False, "error": "No matching transfer found"}
```

---

## Balance Management

Users can prepay to avoid per-request payment friction.

### Database Schema

```sql
-- User balances
CREATE TABLE balances (
    user_id VARCHAR(64) PRIMARY KEY,
    balance DECIMAL(10, 4) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Transaction history
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    type VARCHAR(10) NOT NULL,  -- 'credit' or 'debit'
    amount DECIMAL(10, 4) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Balance Operations

```python
class BalanceService:
    """Manage user prepaid balances."""
    
    async def get_balance(self, user_id: str) -> float:
        """Get current balance."""
        row = await self.db.fetchrow(
            "SELECT balance FROM balances WHERE user_id = $1",
            user_id
        )
        return float(row["balance"]) if row else 0.0
    
    async def add_funds(self, user_id: str, amount: float, source: str):
        """Add funds from payment."""
        await self.db.execute("""
            INSERT INTO balances (user_id, balance)
            VALUES ($1, $2)
            ON CONFLICT (user_id) 
            DO UPDATE SET balance = balances.balance + $2
        """, user_id, amount)
        
        await self.db.execute("""
            INSERT INTO transactions (user_id, type, amount, description)
            VALUES ($1, 'credit', $2, $3)
        """, user_id, amount, f"Top-up via {source}")
    
    async def deduct(self, user_id: str, amount: float, description: str):
        """Deduct for API usage."""
        result = await self.db.execute("""
            UPDATE balances 
            SET balance = balance - $2
            WHERE user_id = $1 AND balance >= $2
        """, user_id, amount)
        
        if result == "UPDATE 0":
            raise InsufficientBalance()
        
        await self.db.execute("""
            INSERT INTO transactions (user_id, type, amount, description)
            VALUES ($1, 'debit', $2, $3)
        """, user_id, amount, description)
```

---

## Client Integration

### Simple SDK

```python
class NodoClient:
    """Client with automatic payment handling."""
    
    def __init__(self, api_key: str, auto_pay: bool = False):
        self.api_key = api_key
        self.auto_pay = auto_pay
        self.lightning_wallet = None  # Optional
    
    async def analyze(self, market_url: str, tier: str = "standard"):
        """Analyze a market, handling payments."""
        
        response = await self.http.post(
            "/api/analyze",
            json={"market": market_url, "tier": tier},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        # Success - return result
        if response.status_code == 200:
            return response.json()
        
        # Payment required
        if response.status_code == 402:
            payment_info = response.json()
            
            if self.auto_pay and self.lightning_wallet:
                # Automatically pay via Lightning
                invoice = payment_info["payment"]["methods"][0]["invoice"]
                preimage = await self.lightning_wallet.pay(invoice)
                
                # Retry with payment proof
                response = await self.http.post(
                    "/api/analyze",
                    json={"market": market_url, "tier": tier},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "X-Payment-Preimage": preimage
                    }
                )
                return response.json()
            
            # Manual payment needed
            raise PaymentRequired(payment_info)
        
        response.raise_for_status()
```

### Usage Example

```python
# Basic usage
client = NodoClient(api_key="your_key")

try:
    result = await client.analyze("polymarket.com/event/btc-150k")
    print(f"Consensus: {result['consensus']['action']}")
except PaymentRequired as e:
    print(f"Payment needed: ${e.amount}")
    print(f"Lightning invoice: {e.lightning_invoice}")

# With auto-pay
client = NodoClient(
    api_key="your_key",
    auto_pay=True
)
client.lightning_wallet = MyLightningWallet()

# This will automatically pay if needed
result = await client.analyze("polymarket.com/event/btc-150k")
```

---

## Security Considerations

### Preventing Double-Spend

For prepaid balances, use database transactions:

```python
async def deduct_atomic(self, user_id: str, amount: float):
    """Atomic deduct - prevents race conditions."""
    
    async with self.db.transaction():
        # Lock row and check balance
        row = await self.db.fetchrow(
            "SELECT balance FROM balances WHERE user_id = $1 FOR UPDATE",
            user_id
        )
        
        if not row or row["balance"] < amount:
            raise InsufficientBalance()
        
        # Deduct
        await self.db.execute(
            "UPDATE balances SET balance = balance - $1 WHERE user_id = $2",
            amount, user_id
        )
```

### Rate Limiting

Even with payments, prevent abuse:

```python
# Limit requests per minute per user
@rate_limit(requests=60, window=60)
async def analyze_endpoint(request):
    ...
```
