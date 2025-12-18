"""
Arbitrage Scanner Service
Finds intra-platform arbitrage opportunities.

Adapted from bot/arbitrage_scanner.py
"""
import json
from typing import Optional, List
from dataclasses import dataclass

import httpx


@dataclass
class Market:
    """Market data."""
    id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    url: str


@dataclass
class ArbitrageOpportunity:
    """An arbitrage opportunity."""
    market: Market
    total_cost: float
    guaranteed_profit: float
    net_profit_pct: float
    strategy: str


class ArbitrageScanner:
    """Scans for arbitrage opportunities."""
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    TRADING_FEE = 0.01  # 1% fee
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
    
    def scan(self, limit: int = 200) -> List[ArbitrageOpportunity]:
        """Scan for arbitrage opportunities."""
        try:
            response = self.client.get(
                f"{self.GAMMA_URL}/markets",
                params={"limit": limit, "active": "true", "closed": "false"}
            )
            response.raise_for_status()
            markets = response.json()
        except Exception as e:
            print(f"Scan error: {e}")
            return []
        
        opportunities = []
        
        for market_data in markets:
            opp = self._analyze_market(market_data)
            if opp:
                opportunities.append(opp)
        
        # Sort by profit
        opportunities.sort(key=lambda x: x.net_profit_pct, reverse=True)
        return opportunities
    
    def _analyze_market(self, market_data: dict) -> Optional[ArbitrageOpportunity]:
        """Analyze a single market for arbitrage."""
        try:
            question = market_data.get("question", "")
            if not question:
                return None
            
            prices_raw = market_data.get("outcomePrices", '["0.5", "0.5"]')
            prices = [float(p) for p in (json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw)]
            
            if len(prices) != 2:
                return None
            
            yes_price, no_price = prices[0], prices[1]
            volume = float(market_data.get("volume", 0))
            
            # Filter low volume
            if volume < 1000:
                return None
            
            # Check for arbitrage: YES + NO < 1.00
            total_cost = yes_price + no_price
            
            if total_cost >= 1.0:
                return None
            
            # Calculate profit (before fees)
            gross_profit = 1.0 - total_cost
            
            # Apply trading fee
            fee_cost = total_cost * self.TRADING_FEE
            net_profit = gross_profit - fee_cost
            
            if net_profit <= 0:
                return None
            
            net_profit_pct = (net_profit / total_cost) * 100
            
            slug = market_data.get("slug", market_data.get("id", ""))
            
            market = Market(
                id=str(market_data.get("id", "")),
                question=question[:100],
                yes_price=yes_price,
                no_price=no_price,
                volume=volume,
                url=f"https://polymarket.com/event/{slug}"
            )
            
            return ArbitrageOpportunity(
                market=market,
                total_cost=round(total_cost, 4),
                guaranteed_profit=round(net_profit, 4),
                net_profit_pct=round(net_profit_pct, 2),
                strategy="BUY_BOTH"
            )
            
        except:
            return None
    
    def close(self):
        self.client.close()


