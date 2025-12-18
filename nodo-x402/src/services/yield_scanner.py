"""
Yield Scanner Service
Finds high-probability events for yield farming.

Copied and adapted from bot/yield_scanner.py
"""
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, List

import httpx


@dataclass
class YieldOpportunity:
    """A yield farming opportunity."""
    market_id: str
    question: str
    outcome: str
    buy_price: float
    profit_pct: float
    days_to_resolution: int
    apy: float
    url: str
    volume: float
    risk_level: str
    
    def to_dict(self) -> dict:
        return asdict(self)


class YieldScanner:
    """Scans Polymarket for yield farming opportunities."""
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    
    def __init__(
        self, 
        min_probability: float = 0.95,
        min_volume: float = 1000,
        max_days: int = 60
    ):
        self.min_probability = min_probability
        self.min_volume = min_volume
        self.max_days = max_days
        self.client = httpx.Client(timeout=30.0)
    
    def scan(self, limit: int = 300) -> List[YieldOpportunity]:
        """Scan for yield opportunities."""
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
        for market in markets:
            opp = self._analyze_market(market)
            if opp:
                opportunities.append(opp)
        
        opportunities.sort(key=lambda x: x.apy, reverse=True)
        return opportunities
    
    def _analyze_market(self, market: dict) -> Optional[YieldOpportunity]:
        """Analyze a single market."""
        try:
            # Parse data
            outcomes_raw = market.get("outcomes", '["Yes", "No"]')
            prices_raw = market.get("outcomePrices", '["0.5", "0.5"]')
            
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            prices = [float(p) for p in (json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw)]
            
            if len(outcomes) != 2:
                return None
            
            # Find high probability outcome
            yes_price, no_price = prices[0], prices[1]
            
            if yes_price >= self.min_probability:
                outcome, buy_price = "YES", yes_price
            elif no_price >= self.min_probability:
                outcome, buy_price = "NO", no_price
            else:
                return None
            
            if buy_price >= 0.995:
                return None
            
            # Volume filter
            volume = float(market.get("volume", 0))
            if volume < self.min_volume:
                return None
            
            # Calculate profit
            profit_pct = ((1.0 - buy_price) / buy_price) * 100
            
            # Days to resolution
            end_date_str = market.get("endDate")
            if not end_date_str:
                return None
            
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                days = max(1, (end_date - datetime.now(timezone.utc)).days)
            except:
                days = 30
            
            if days > self.max_days:
                return None
            
            # APY
            apy = (profit_pct / days) * 365
            
            # Risk level
            if buy_price >= 0.97:
                risk = "LOW"
            elif buy_price >= 0.95:
                risk = "MEDIUM"
            else:
                risk = "HIGH"
            
            slug = market.get("slug", market.get("id", ""))
            
            return YieldOpportunity(
                market_id=str(market.get("id", "")),
                question=market.get("question", "")[:80],
                outcome=outcome,
                buy_price=buy_price,
                profit_pct=round(profit_pct, 2),
                days_to_resolution=days,
                apy=round(apy, 1),
                url=f"https://polymarket.com/event/{slug}",
                volume=volume,
                risk_level=risk
            )
        except:
            return None
    
    def close(self):
        self.client.close()


