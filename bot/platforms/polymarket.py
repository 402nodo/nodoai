"""
Polymarket Platform Integration
https://polymarket.com
"""
import json
import httpx
from typing import Optional
from datetime import datetime
from loguru import logger

from .base import PredictionPlatform, PlatformMarket, PlatformOutcome, MarketCategory


class PolymarketPlatform(PredictionPlatform):
    """
    Polymarket - Decentralized prediction market on Polygon.
    https://docs.polymarket.com
    """
    
    name = "polymarket"
    base_url = "https://polymarket.com"
    gamma_url = "https://gamma-api.polymarket.com"
    clob_url = "https://clob.polymarket.com"
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
    
    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()
    
    @property
    def is_decentralized(self) -> bool:
        return True
    
    @property
    def trading_fee(self) -> float:
        return 0.02  # 2% on winnings
    
    def get_markets(self, limit: int = 100, **kwargs) -> list[PlatformMarket]:
        """Fetch markets from Polymarket Gamma API."""
        try:
            params = {
                "limit": limit,
                "active": "true",
                "closed": "false"
            }
            
            response = self.client.get(f"{self.gamma_url}/markets", params=params)
            response.raise_for_status()
            data = response.json()
            
            markets = []
            for item in data:
                market = self._parse_market(item)
                if market:
                    markets.append(market)
            
            logger.info(f"[Polymarket] Fetched {len(markets)} markets")
            return markets
            
        except httpx.HTTPError as e:
            logger.error(f"[Polymarket] Failed to fetch markets: {e}")
            return []
    
    def get_market_by_id(self, market_id: str) -> Optional[PlatformMarket]:
        """Fetch specific market by ID."""
        try:
            response = self.client.get(f"{self.gamma_url}/markets/{market_id}")
            response.raise_for_status()
            return self._parse_market(response.json())
        except httpx.HTTPError as e:
            logger.error(f"[Polymarket] Failed to fetch market {market_id}: {e}")
            return None
    
    def search_markets(self, query: str, limit: int = 20) -> list[PlatformMarket]:
        """Search markets by keyword."""
        try:
            params = {
                "limit": limit,
                "active": "true",
                "_q": query
            }
            response = self.client.get(f"{self.gamma_url}/markets", params=params)
            response.raise_for_status()
            
            markets = []
            for item in response.json():
                market = self._parse_market(item)
                if market:
                    markets.append(market)
            return markets
            
        except httpx.HTTPError as e:
            logger.error(f"[Polymarket] Search failed: {e}")
            return []
    
    def _parse_market(self, data: dict) -> Optional[PlatformMarket]:
        """Parse Polymarket API response to PlatformMarket."""
        try:
            # Parse outcomes (JSON string)
            outcomes_raw = data.get("outcomes", '["Yes", "No"]')
            if isinstance(outcomes_raw, str):
                outcome_names = json.loads(outcomes_raw)
            else:
                outcome_names = outcomes_raw
            
            # Parse prices (JSON string)
            prices_raw = data.get("outcomePrices", '["0.5", "0.5"]')
            if isinstance(prices_raw, str):
                prices = [float(p) for p in json.loads(prices_raw)]
            else:
                prices = [float(p) for p in prices_raw]
            
            # Create outcomes
            outcomes = []
            for i, name in enumerate(outcome_names):
                price = prices[i] if i < len(prices) else 0.5
                outcomes.append(PlatformOutcome(name=name, price=price))
            
            if len(outcomes) < 2:
                return None
            
            # Parse dates
            end_date = None
            if data.get("endDate"):
                try:
                    end_date = datetime.fromisoformat(data["endDate"].replace("Z", "+00:00"))
                except:
                    pass
            
            # Extract keywords from question
            question = data.get("question", "")
            keywords = self._extract_keywords(question)
            
            return PlatformMarket(
                platform=self.name,
                market_id=str(data.get("id", data.get("conditionId", ""))),
                question=question,
                description=data.get("description", "")[:500],
                slug=data.get("slug", ""),
                url=f"{self.base_url}/event/{data.get('slug', '')}",
                outcomes=outcomes,
                category=self._categorize(question),
                volume=float(data.get("volume", data.get("volumeNum", 0))),
                liquidity=float(data.get("liquidity", data.get("liquidityNum", 0))),
                end_date=end_date,
                active=data.get("active", True),
                resolved=data.get("closed", False),
                keywords=keywords
            )
            
        except Exception as e:
            logger.warning(f"[Polymarket] Failed to parse market: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract searchable keywords from text."""
        # Simple keyword extraction
        import re
        words = re.findall(r'\b[A-Z][a-z]+\b|\b[A-Z]{2,}\b', text)
        return list(set(words))[:10]
    
    def _categorize(self, question: str) -> MarketCategory:
        """Categorize market by question content."""
        q = question.lower()
        
        if any(w in q for w in ["trump", "biden", "election", "president", "congress", "vote"]):
            return MarketCategory.POLITICS
        elif any(w in q for w in ["bitcoin", "btc", "eth", "crypto", "token", "defi"]):
            return MarketCategory.CRYPTO
        elif any(w in q for w in ["nfl", "nba", "mlb", "super bowl", "championship", "game"]):
            return MarketCategory.SPORTS
        elif any(w in q for w in ["fed", "rate", "inflation", "gdp", "recession", "economy"]):
            return MarketCategory.ECONOMICS
        elif any(w in q for w in ["oscar", "grammy", "movie", "album", "celebrity"]):
            return MarketCategory.ENTERTAINMENT
        
        return MarketCategory.OTHER

