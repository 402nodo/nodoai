# x402 Payment Flow on Solana

## Overview

x402 is an implementation of HTTP 402 (Payment Required) using Solana USDC for micropayments. This document explains how payments work in the NODO x402 API.

## Payment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        x402 Payment Flow                             │
└─────────────────────────────────────────────────────────────────────┘

┌──────────┐       ┌──────────────┐       ┌─────────────┐
│  Client  │       │  NODO API    │       │   Solana    │
│  (SDK)   │       │  Server      │       │   Network   │
└────┬─────┘       └──────┬───────┘       └──────┬──────┘
     │                    │                      │
     │  1. POST /analyze  │                      │
     │───────────────────>│                      │
     │                    │                      │
     │  2. 402 Payment    │                      │
     │     Required       │                      │
     │<───────────────────│                      │
     │                    │                      │
     │  {                 │                      │
     │    payment: {      │                      │
     │      amount: 0.10, │                      │
     │      recipient,    │                      │
     │      memo          │                      │
     │    }               │                      │
     │  }                 │                      │
     │                    │                      │
     │  3. USDC Transfer  │                      │
     │───────────────────────────────────────────>│
     │                    │                      │
     │  4. Tx Signature   │                      │
     │<──────────────────────────────────────────│
     │                    │                      │
     │  5. Retry with     │                      │
     │     X-Payment-Tx   │                      │
     │───────────────────>│                      │
     │                    │  6. Verify Tx        │
     │                    │─────────────────────>│
     │                    │<─────────────────────│
     │                    │                      │
     │  7. 200 OK         │                      │
     │     + Response     │                      │
     │<───────────────────│                      │
     │                    │                      │
```

## Step-by-Step

### 1. Client Makes Request

```bash
curl -X POST https://api.nodo.ai/x402/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"market": "polymarket.com/event/btc-150k", "tier": "deep"}'
```

### 2. Server Returns 402

```json
HTTP/1.1 402 Payment Required

{
  "error": {
    "code": "PAYMENT_REQUIRED",
    "message": "This request requires payment of $0.10 USDC"
  },
  "payment": {
    "x402_version": 1,
    "network": "solana-mainnet",
    "amount": "0.100000",
    "currency": "USDC",
    "decimals": 6,
    "recipient": "NoDo7nX4t2QGKDC7B9a3qRhCmj8K8vM9HwxAJpKgZrMw",
    "usdc_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "memo": "req_a1b2c3d4e5f6",
    "expires_at": "2025-12-19T12:05:00Z"
  }
}
```

### 3. Client Sends USDC

The client creates and sends a Solana transaction:

```typescript
// Using @solana/web3.js and @solana/spl-token
const tx = new Transaction();

// Optional: Add memo for tracking
tx.add(createMemoInstruction(payment.memo));

// Add USDC transfer
tx.add(
  createTransferCheckedInstruction(
    senderTokenAccount,
    USDC_MINT,
    recipientTokenAccount,
    senderPublicKey,
    amountInLamports, // 100000 for $0.10
    6 // USDC decimals
  )
);

const signature = await connection.sendTransaction(tx, [keypair]);
```

### 4. Client Gets Signature

```
Transaction Signature: 5K7mNvuKR9vAqJNkqRV3f8W...
```

### 5. Client Retries with Proof

```bash
curl -X POST https://api.nodo.ai/x402/v1/analyze \
  -H "Content-Type: application/json" \
  -H "X-Payment-Tx: 5K7mNvuKR9vAqJNkqRV3f8W..." \
  -d '{"market": "polymarket.com/event/btc-150k", "tier": "deep"}'
```

### 6. Server Verifies Transaction

The server checks:
- Transaction exists on Solana
- Transaction is confirmed (not failed)
- Transfer is to correct recipient
- Amount is correct (±0.000001 tolerance)
- Transaction is recent (< 5 minutes old)
- Transaction hasn't been used before (replay protection)

### 7. Server Returns Response

```json
HTTP/1.1 200 OK

{
  "market": {...},
  "analysis": {
    "consensus": "BUY_NO",
    "agreement": "5/6",
    "confidence": 82
  },
  "models": [...],
  "meta": {
    "request_id": "req_a1b2c3d4e5f6",
    "cost": "$0.10",
    "network": "solana",
    "tx_signature": "5K7mNvuKR9vAqJNkqRV3f8W..."
  }
}
```

## SDK Handling

Both Python and TypeScript SDKs handle this automatically:

```python
# Python - Auto-payment enabled by default
client = NodoClient(keypair_path="~/.config/solana/id.json")
result = await client.analyze(market="...", tier="deep")  # Payment handled automatically
```

```typescript
// TypeScript - Auto-payment enabled by default
const client = new NodoClient({ keypair: keypair.secretKey });
const result = await client.analyze({ market: '...', tier: 'deep' });  // Payment handled automatically
```

## Manual Payment Mode

For applications that need custom payment handling:

```python
client = NodoClient(auto_pay=False)

try:
    result = await client.analyze(market="...")
except PaymentRequired as e:
    print(f"Send ${e.amount} USDC to {e.recipient}")
    print(f"Include memo: {e.memo}")
    
    # Handle payment externally
    tx_signature = my_payment_handler(e.recipient, e.amount, e.memo)
    
    # Retry with proof
    result = await client.analyze(
        market="...",
        headers={"X-Payment-Tx": tx_signature}
    )
```

## Security Considerations

### For API Consumers

1. **Keypair Security**: Never expose your Solana private key
2. **Amount Verification**: Always verify the requested amount before paying
3. **Recipient Verification**: Check that recipient matches expected NODO address
4. **Timeout Handling**: Payments expire after ~5 minutes

### For API Providers

1. **Transaction Verification**: Always verify on-chain, never trust headers alone
2. **Replay Protection**: Track used transaction signatures
3. **Amount Tolerance**: Allow small floating-point variance
4. **Rate Limiting**: Limit verification requests per wallet

## Advantages of x402 on Solana

| Feature | x402 Solana | Traditional Billing |
|---------|-------------|---------------------|
| Finality | 400ms | Days |
| Min Payment | $0.001 | $1-10 |
| Fees | $0.00025 | $0.30+ |
| Setup | None | Account creation |
| Geographic | Global | Limited |
| AI Agent Ready | ✅ | ❌ |


