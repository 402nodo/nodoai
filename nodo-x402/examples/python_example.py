#!/usr/bin/env python3
"""
NODO x402 Python SDK Example
Demonstrates AI analysis with automatic Solana USDC payments.
"""
import asyncio
import os
from pathlib import Path

# Add SDK to path for local development
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk" / "python"))

from nodo_x402 import NodoClient, PaymentRequired


async def main():
    """Main example function."""
    
    print("=" * 60)
    print("  NODO x402 - AI Prediction Market Analysis")
    print("  Powered by Solana Micropayments")
    print("=" * 60)
    print()
    
    # Initialize client
    # For production, use your Solana keypair:
    # client = NodoClient(keypair_path="~/.config/solana/id.json")
    
    # For this example, we'll use manual payment mode
    client = NodoClient(
        base_url="http://localhost:8000",  # Local development
        auto_pay=False,  # Manual payment for demo
    )
    
    try:
        # ==================
        # 1. AI Analysis
        # ==================
        print("[1] AI Multi-Model Analysis")
        print("-" * 40)
        
        try:
            result = await client.analyze(
                market="polymarket.com/event/btc-150k-2025",
                tier="deep",  # Use all 6 AI models
            )
            
            print(f"Market: {result.market_question}")
            print(f"Consensus: {result.consensus}")
            print(f"Agreement: {result.agreement}")
            print(f"Confidence: {result.confidence}%")
            print()
            
            print("Model Votes:")
            for model in result.models:
                print(f"  • {model.name}: {model.action} ({model.confidence}%)")
            
            if result.dissent:
                print(f"\nDissent: {result.dissent.model} says {result.dissent.action}")
                print(f"  Reason: {result.dissent.reason}")
            
            print(f"\nCost: {result.cost}")
            
        except PaymentRequired as e:
            print(f"💳 Payment Required: ${e.amount} USDC")
            print(f"   Recipient: {e.recipient}")
            print(f"   Memo: {e.memo}")
            print("   (In auto_pay mode, this would be handled automatically)")
        
        print()
        
        # ==================
        # 2. Yield Scanner
        # ==================
        print("[2] Yield Farming Scanner")
        print("-" * 40)
        
        try:
            opportunities = await client.yield_scan(
                min_probability=0.95,
                min_volume=10000,
                risk_level="LOW",
                limit=5,
            )
            
            print(f"Found {len(opportunities)} opportunities:")
            for i, opp in enumerate(opportunities, 1):
                print(f"\n{i}. {opp.question}")
                print(f"   Buy {opp.outcome} @ ${opp.buy_price:.3f}")
                print(f"   Profit: {opp.profit_pct:.2f}% | APY: {opp.apy:.0f}%")
                print(f"   Days: {opp.days_to_resolution} | Risk: {opp.risk_level}")
                
        except PaymentRequired as e:
            print(f"💳 Payment Required: ${e.amount} USDC")
        
        print()
        
        # ==================
        # 3. Delta Scanner
        # ==================
        print("[3] Delta Neutral Scanner (Mispricing)")
        print("-" * 40)
        
        try:
            deltas = await client.delta_scan(
                min_profit=5.0,
                topic="BTC",
                limit=3,
            )
            
            print(f"Found {len(deltas)} mispricing opportunities:")
            for i, d in enumerate(deltas, 1):
                print(f"\n{i}. [{d.topic}] {d.logic_error}")
                print(f"   Profit Potential: {d.profit_potential:.1f}%")
                print(f"   Confidence: {d.confidence}%")
                print(f"   Action: {d.action}")
                
        except PaymentRequired as e:
            print(f"💳 Payment Required: ${e.amount} USDC")
        
        print()
        
        # ==================
        # 4. Market Data
        # ==================
        print("[4] Market Data")
        print("-" * 40)
        
        try:
            markets = await client.get_markets(
                platform="polymarket",
                min_volume=100000,
                search="bitcoin",
                limit=3,
            )
            
            print(f"Found {len(markets)} markets:")
            for m in markets:
                print(f"\n• {m.question}")
                print(f"  YES: ${m.yes_price:.2f} | NO: ${m.no_price:.2f}")
                print(f"  Volume: ${m.volume:,.0f}")
                
        except PaymentRequired as e:
            print(f"💳 Payment Required: ${e.amount} USDC")
        
        print()
        
        # ==================
        # 5. Pricing Info
        # ==================
        print("[5] API Pricing")
        print("-" * 40)
        
        pricing = await client.get_pricing()
        print("AI Analysis:")
        for tier, info in pricing.get("pricing", {}).get("ai_analysis", {}).items():
            print(f"  • {tier}: ${info.get('price', 'N/A')} ({info.get('models', '?')} models)")
        
        print("\nScanners:")
        for scanner, price in pricing.get("pricing", {}).get("scanners", {}).items():
            print(f"  • {scanner}: ${price}")
        
    finally:
        await client.close()
    
    print()
    print("=" * 60)
    print("  Demo complete! Check https://nodo.ai for more info")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


