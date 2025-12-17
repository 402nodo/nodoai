"""
PredictIt Platform Integration
https://predictit.org - Political prediction market
"""
import httpx
from typing import Optional
from datetime import datetime
from loguru import logger

from .base import PredictionPlatform, PlatformMarket, PlatformOutcome, MarketCategory


class PredictItPlatform(PredictionPlatform):
    """
    PredictIt - Political prediction market.
    https://www.predictit.org/api/marketdata/all/
    
    Note: PredictIt has public API but trading has geographic restrictions.
    """
    
    name = "predictit"
    base_url = "https://www.predictit.org"
    api_url = "https://www.predictit.org/api/marketdata"
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
    
    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()
    
    @property
    def is_decentralized(self) -> bool:
        return False
    
    @property
    def trading_fee(self) -> float:
        return 0.10  # 10% on profits + 5% withdrawal
    
    def get_markets(self, limit: int = 100, **kwargs) -> list[PlatformMarket]:
        """Fetch all markets from PredictIt."""
        try:
            response = self.client.get(f"{self.api_url}/all/")
            response.raise_for_status()
            data = response.json()
            
            markets = []
            market_list = data.get("markets", [])
            
            for item in market_list[:limit]:
                parsed_markets = self._parse_market(item)
                markets.extend(parsed_markets)
            
            logger.info(f"[PredictIt] Fetched {len(markets)} markets")
            return markets
            
        except httpx.HTTPError as e:
            logger.error(f"[PredictIt] Failed to fetch markets: {e}")
            return []
    
    def get_market_by_id(self, market_id: str) -> Optional[PlatformMarket]:
        """Fetch specific market by ID."""
        try:
            response = self.client.get(f"{self.api_url}/markets/{market_id}")
            response.raise_for_status()
            data = response.json()
            
            markets = self._parse_market(data)
            return markets[0] if markets else None
            
        except httpx.HTTPError as e:
            logger.error(f"[PredictIt] Failed to fetch market {market_id}: {e}")
            return None
    
    def search_markets(self, query: str, limit: int = 20) -> list[PlatformMarket]:
        """Search markets by keyword."""
        markets = self.get_markets(limit=500)
        query_lower = query.lower()
        
        matching = []
        for market in markets:
            if query_lower in market.question.lower():
                matching.append(market)
                if len(matching) >= limit:
                    break
        
        return matching
    
    def _parse_market(self, data: dict) -> list[PlatformMarket]:
        """
        Parse PredictIt market to PlatformMarket(s).
        
        PredictIt markets can have multiple contracts (candidates).
        Each contract becomes a separate market for our purposes.
        """
        markets = []
        
        try:
            market_id = str(data.get("id", ""))
            market_name = data.get("name", data.get("shortName", ""))
            market_url = data.get("url", f"{self.base_url}/markets/detail/{market_id}")
            
            contracts = data.get("contracts", [])
            
            # For binary markets (single contract)
            if len(contracts) == 1:
                contract = contracts[0]
                yes_price = float(contract.get("lastTradePrice", contract.get("bestBuyYesCost", 0.5)))
                no_price = 1.0 - yes_price
                
                outcomes = [
                    PlatformOutcome(name="Yes", price=yes_price),
                    PlatformOutcome(name="No", price=no_price)
                ]
                
                markets.append(PlatformMarket(
                    platform=self.name,
                    market_id=market_id,
                    question=market_name,
                    description=data.get("shortName", ""),
                    url=market_url,
                    outcomes=outcomes,
                    category=MarketCategory.POLITICS,
                    volume=0,  # PredictIt doesn't expose volume easily
                    active=data.get("status") == "Open",
                    keywords=self._extract_keywords(market_name)
                ))
            
            # For multi-contract markets (e.g., "Who will win X?")
            elif len(contracts) > 1:
                outcomes = []
                for contract in contracts:
                    name = contract.get("name", contract.get("shortName", "Unknown"))
                    price = float(contract.get("lastTradePrice", contract.get("bestBuyYesCost", 0)))
                    
                    outcomes.append(PlatformOutcome(
                        name=name,
                        price=price,
                        token_id=str(contract.get("id", ""))
                    ))
                
                if outcomes:
                    markets.append(PlatformMarket(
                        platform=self.name,
                        market_id=market_id,
                        question=market_name,
                        description=data.get("shortName", ""),
                        url=market_url,
                        outcomes=outcomes,
                        category=MarketCategory.POLITICS,
                        volume=0,
                        active=data.get("status") == "Open",
                        keywords=self._extract_keywords(market_name)
                    ))
            
            return markets
            
        except Exception as e:
            logger.warning(f"[PredictIt] Failed to parse market: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords."""
        import re
        words = re.findall(r'\b[A-Z][a-z]+\b|\b[A-Z]{2,}\b', text)
        return list(set(words))[:10]

