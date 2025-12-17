"""
Kalshi Platform Integration
https://kalshi.com - CFTC regulated prediction market
"""
import httpx
from typing import Optional
from datetime import datetime
from loguru import logger

from .base import PredictionPlatform, PlatformMarket, PlatformOutcome, MarketCategory


class KalshiPlatform(PredictionPlatform):
    """
    Kalshi - CFTC regulated prediction market.
    https://trading-api.readme.io/reference/getmarkets
    
    Note: Kalshi requires authentication for trading but 
    market data is publicly available.
    """
    
    name = "kalshi"
    base_url = "https://kalshi.com"
    api_url = "https://api.elections.kalshi.com/trade-api/v2"  # Public API
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
        
    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()
    
    @property
    def is_decentralized(self) -> bool:
        return False  # Centralized, regulated
    
    @property
    def trading_fee(self) -> float:
        return 0.01  # ~1% (varies by contract)
    
    def get_markets(self, limit: int = 100, **kwargs) -> list[PlatformMarket]:
        """
        Fetch markets from Kalshi API.
        
        Note: Kalshi API structure may vary. This uses their public endpoints.
        """
        try:
            # Kalshi uses different endpoint structure
            params = {
                "limit": limit,
                "status": "open"
            }
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = self.client.get(
                f"{self.api_url}/markets",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            markets = []
            market_list = data.get("markets", data) if isinstance(data, dict) else data
            
            for item in market_list[:limit]:
                market = self._parse_market(item)
                if market:
                    markets.append(market)
            
            logger.info(f"[Kalshi] Fetched {len(markets)} markets")
            return markets
            
        except httpx.HTTPError as e:
            logger.error(f"[Kalshi] Failed to fetch markets: {e}")
            return []
    
    def get_market_by_id(self, market_id: str) -> Optional[PlatformMarket]:
        """Fetch specific market by ticker."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = self.client.get(
                f"{self.api_url}/markets/{market_id}",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_market(data.get("market", data))
            
        except httpx.HTTPError as e:
            logger.error(f"[Kalshi] Failed to fetch market {market_id}: {e}")
            return None
    
    def search_markets(self, query: str, limit: int = 20) -> list[PlatformMarket]:
        """Search markets - Kalshi may not have direct search, filter locally."""
        markets = self.get_markets(limit=200)
        query_lower = query.lower()
        
        matching = []
        for market in markets:
            if query_lower in market.question.lower():
                matching.append(market)
                if len(matching) >= limit:
                    break
        
        return matching
    
    def _parse_market(self, data: dict) -> Optional[PlatformMarket]:
        """Parse Kalshi API response to PlatformMarket."""
        try:
            # Kalshi uses 'ticker' as market ID
            market_id = data.get("ticker", data.get("id", ""))
            
            # Title/question
            question = data.get("title", data.get("question", ""))
            if not question:
                return None
            
            # Prices - Kalshi uses yes_bid, yes_ask, no_bid, no_ask or similar
            yes_price = data.get("yes_bid", data.get("last_price", 0.5))
            if isinstance(yes_price, str):
                yes_price = float(yes_price) / 100  # Kalshi may use cents
            elif yes_price > 1:
                yes_price = yes_price / 100
            
            no_price = 1.0 - yes_price
            
            # Some Kalshi endpoints have different price format
            if "yes_ask" in data:
                yes_price = float(data["yes_ask"]) / 100
            if "last_price" in data and data["last_price"] is not None:
                price = data["last_price"]
                if price > 1:
                    price = price / 100
                yes_price = price
                no_price = 1.0 - yes_price
            
            outcomes = [
                PlatformOutcome(name="Yes", price=yes_price),
                PlatformOutcome(name="No", price=no_price)
            ]
            
            # Parse dates
            end_date = None
            for date_field in ["close_time", "expiration_time", "end_date"]:
                if data.get(date_field):
                    try:
                        end_date = datetime.fromisoformat(
                            data[date_field].replace("Z", "+00:00")
                        )
                        break
                    except:
                        pass
            
            # Volume
            volume = float(data.get("volume", data.get("dollar_volume", 0)))
            
            # Keywords
            keywords = self._extract_keywords(question)
            
            return PlatformMarket(
                platform=self.name,
                market_id=market_id,
                question=question,
                description=data.get("subtitle", data.get("description", ""))[:500],
                slug=data.get("ticker_name", market_id),
                url=f"{self.base_url}/markets/{market_id}",
                outcomes=outcomes,
                category=self._categorize(question),
                volume=volume,
                liquidity=float(data.get("open_interest", 0)),
                end_date=end_date,
                active=data.get("status") == "open" or data.get("active", True),
                resolved=data.get("status") == "closed",
                keywords=keywords
            )
            
        except Exception as e:
            logger.warning(f"[Kalshi] Failed to parse market: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        import re
        words = re.findall(r'\b[A-Z][a-z]+\b|\b[A-Z]{2,}\b', text)
        return list(set(words))[:10]
    
    def _categorize(self, question: str) -> MarketCategory:
        """Categorize market."""
        q = question.lower()
        
        if any(w in q for w in ["trump", "biden", "election", "president", "congress"]):
            return MarketCategory.POLITICS
        elif any(w in q for w in ["bitcoin", "btc", "crypto"]):
            return MarketCategory.CRYPTO
        elif any(w in q for w in ["nfl", "nba", "sports"]):
            return MarketCategory.SPORTS
        elif any(w in q for w in ["fed", "rate", "inflation", "gdp", "recession"]):
            return MarketCategory.ECONOMICS
        
        return MarketCategory.OTHER

