"""
Market Data Service
Fetches market data from prediction platforms.
"""
import json
from typing import Optional, List, Dict, Any

import httpx
from loguru import logger


class MarketDataService:
    """Service for fetching market data from multiple platforms."""
    
    POLYMARKET_URL = "https://gamma-api.polymarket.com"
    KALSHI_URL = "https://api.elections.kalshi.com/trade-api/v2"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_markets(
        self,
        platform: str = "polymarket",
        active: bool = True,
        min_volume: float = 0,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get list of markets from a platform."""
        
        if platform == "polymarket":
            return await self._get_polymarket_markets(
                active, min_volume, category, search, limit, offset
            )
        elif platform == "kalshi":
            return await self._get_kalshi_markets(
                active, min_volume, category, search, limit, offset
            )
        else:
            return []
    
    async def get_market(
        self,
        platform: str,
        market_id: str,
        include_orderbook: bool = False,
        include_history: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed market info."""
        
        if platform == "polymarket":
            return await self._get_polymarket_market(
                market_id, include_orderbook, include_history
            )
        elif platform == "kalshi":
            return await self._get_kalshi_market(
                market_id, include_orderbook, include_history
            )
        return None
    
    async def _get_polymarket_markets(
        self,
        active: bool,
        min_volume: float,
        category: Optional[str],
        search: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Dict]:
        """Fetch markets from Polymarket."""
        try:
            params = {
                "limit": min(limit * 2, 500),  # Fetch extra for filtering
                "offset": offset,
                "active": str(active).lower(),
            }
            
            response = await self.client.get(
                f"{self.POLYMARKET_URL}/markets",
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"Polymarket API error: {response.status_code}")
                return []
            
            markets = response.json()
            
            # Parse and filter
            results = []
            for m in markets:
                try:
                    prices_raw = m.get("outcomePrices", '["0.5", "0.5"]')
                    prices = [float(p) for p in (json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw)]
                    
                    volume = float(m.get("volume", 0))
                    
                    # Apply filters
                    if volume < min_volume:
                        continue
                    
                    question = m.get("question", "")
                    if search and search.lower() not in question.lower():
                        continue
                    
                    slug = m.get("slug", m.get("id", ""))
                    
                    results.append({
                        "id": str(m.get("id", "")),
                        "question": question,
                        "yes_price": prices[0] if len(prices) > 0 else 0.5,
                        "no_price": prices[1] if len(prices) > 1 else 0.5,
                        "volume": volume,
                        "liquidity": float(m.get("liquidity", 0)),
                        "end_date": m.get("endDate"),
                        "category": m.get("groupSlug"),
                        "url": f"https://polymarket.com/event/{slug}"
                    })
                    
                    if len(results) >= limit:
                        break
                        
                except Exception as e:
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Polymarket fetch error: {e}")
            return []
    
    async def _get_polymarket_market(
        self,
        market_id: str,
        include_orderbook: bool,
        include_history: bool,
    ) -> Optional[Dict]:
        """Fetch single market from Polymarket."""
        try:
            # Try by slug first
            response = await self.client.get(
                f"{self.POLYMARKET_URL}/markets",
                params={"slug": market_id, "limit": 1}
            )
            
            if response.status_code != 200:
                # Try by ID
                response = await self.client.get(
                    f"{self.POLYMARKET_URL}/markets/{market_id}"
                )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            m = data[0] if isinstance(data, list) else data
            
            prices_raw = m.get("outcomePrices", '["0.5", "0.5"]')
            prices = [float(p) for p in (json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw)]
            
            result = {
                "id": str(m.get("id", "")),
                "question": m.get("question", ""),
                "yes_price": prices[0] if len(prices) > 0 else 0.5,
                "no_price": prices[1] if len(prices) > 1 else 0.5,
                "volume": float(m.get("volume", 0)),
                "liquidity": float(m.get("liquidity", 0)),
                "end_date": m.get("endDate"),
                "category": m.get("groupSlug"),
                "url": f"https://polymarket.com/event/{m.get('slug', market_id)}"
            }
            
            # TODO: Add orderbook and history if requested
            if include_orderbook:
                result["orderbook"] = {"note": "Orderbook data coming soon"}
            if include_history:
                result["history"] = []
            
            return result
            
        except Exception as e:
            logger.error(f"Polymarket market fetch error: {e}")
            return None
    
    async def _get_kalshi_markets(
        self,
        active: bool,
        min_volume: float,
        category: Optional[str],
        search: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Dict]:
        """Fetch markets from Kalshi."""
        try:
            params = {
                "limit": limit,
                "cursor": str(offset) if offset else None,
            }
            
            if active:
                params["status"] = "active"
            
            response = await self.client.get(
                f"{self.KALSHI_URL}/markets",
                params={k: v for k, v in params.items() if v}
            )
            
            if response.status_code != 200:
                logger.warning(f"Kalshi API: {response.status_code}")
                return []
            
            data = response.json()
            markets = data.get("markets", [])
            
            results = []
            for m in markets:
                try:
                    yes_price = float(m.get("yes_ask", 0.5))
                    no_price = float(m.get("no_ask", 0.5))
                    volume = float(m.get("volume", 0))
                    
                    if volume < min_volume:
                        continue
                    
                    title = m.get("title", "")
                    if search and search.lower() not in title.lower():
                        continue
                    
                    results.append({
                        "id": m.get("ticker", ""),
                        "question": title,
                        "yes_price": yes_price,
                        "no_price": no_price,
                        "volume": volume,
                        "end_date": m.get("close_time"),
                        "category": m.get("category"),
                        "url": f"https://kalshi.com/markets/{m.get('ticker', '')}"
                    })
                except:
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Kalshi fetch error: {e}")
            return []
    
    async def _get_kalshi_market(
        self,
        market_id: str,
        include_orderbook: bool,
        include_history: bool,
    ) -> Optional[Dict]:
        """Fetch single market from Kalshi."""
        try:
            response = await self.client.get(
                f"{self.KALSHI_URL}/markets/{market_id}"
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            m = data.get("market", data)
            
            return {
                "id": m.get("ticker", ""),
                "question": m.get("title", ""),
                "yes_price": float(m.get("yes_ask", 0.5)),
                "no_price": float(m.get("no_ask", 0.5)),
                "volume": float(m.get("volume", 0)),
                "end_date": m.get("close_time"),
                "category": m.get("category"),
                "url": f"https://kalshi.com/markets/{m.get('ticker', market_id)}"
            }
            
        except Exception as e:
            logger.error(f"Kalshi market fetch error: {e}")
            return None
    
    async def close(self):
        await self.client.aclose()


