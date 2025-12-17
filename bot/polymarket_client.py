"""
Polymarket API Client
Handles all interactions with Polymarket CLOB and Gamma APIs.
"""
import json
import httpx
from typing import Optional
from dataclasses import dataclass
from loguru import logger

from config import config


@dataclass
class Market:
    """Represents a Polymarket market."""
    id: str
    question: str
    slug: str
    active: bool
    closed: bool
    outcomes: list[str]
    outcome_prices: list[float]  # Prices for each outcome (0-1)
    volume: float
    liquidity: float
    end_date: Optional[str] = None
    
    @property
    def total_price(self) -> float:
        """Sum of all outcome prices. Should be ~1.0 for efficient market."""
        return sum(self.outcome_prices)
    
    @property
    def arbitrage_opportunity(self) -> float:
        """
        Calculate arbitrage opportunity.
        If total_price < 1.0, there's potential profit.
        Returns potential profit in % (e.g., 2.0 = 2%)
        """
        if self.total_price < 1.0:
            # Profit = (1 - total_price) / total_price * 100
            return ((1.0 - self.total_price) / self.total_price) * 100
        return 0.0
    
    @property
    def has_arbitrage(self) -> bool:
        """Check if market has arbitrage above threshold."""
        return self.arbitrage_opportunity > config.MIN_PROFIT_THRESHOLD


@dataclass 
class TokenInfo:
    """Token information for a market outcome."""
    token_id: str
    outcome: str
    price: float
    winner: Optional[bool] = None


class PolymarketClient:
    """
    Client for interacting with Polymarket APIs.
    
    Uses two APIs:
    - Gamma API: For market discovery and metadata
    - CLOB API: For orderbook data and trading
    """
    
    def __init__(self):
        self.gamma_url = config.POLYMARKET_GAMMA_URL
        self.clob_url = config.POLYMARKET_API_URL
        self.client = httpx.Client(timeout=30.0)
        
    def __del__(self):
        """Cleanup HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
    
    def get_markets(self, limit: int = 100, active: bool = True) -> list[Market]:
        """
        Fetch markets from Gamma API.
        
        Args:
            limit: Maximum number of markets to fetch
            active: Only fetch active markets
            
        Returns:
            List of Market objects
        """
        try:
            params = {
                "limit": limit,
                "active": str(active).lower(),
                "closed": "false"
            }
            
            response = self.client.get(
                f"{self.gamma_url}/markets",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            markets = []
            for item in data:
                market = self._parse_market(item)
                if market:
                    markets.append(market)
            
            logger.info(f"Fetched {len(markets)} markets from Polymarket")
            return markets
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []
    
    def get_market_by_id(self, market_id: str) -> Optional[Market]:
        """Fetch a specific market by ID."""
        try:
            response = self.client.get(f"{self.gamma_url}/markets/{market_id}")
            response.raise_for_status()
            data = response.json()
            return self._parse_market(data)
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch market {market_id}: {e}")
            return None
    
    def get_orderbook(self, token_id: str) -> dict:
        """
        Fetch orderbook for a specific token from CLOB API.
        
        Args:
            token_id: The token ID (outcome) to get orderbook for
            
        Returns:
            Orderbook data with bids and asks
        """
        try:
            response = self.client.get(
                f"{self.clob_url}/book",
                params={"token_id": token_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch orderbook for {token_id}: {e}")
            return {"bids": [], "asks": []}
    
    def get_prices(self, token_ids: list[str]) -> dict[str, float]:
        """
        Get current prices for multiple tokens.
        
        Args:
            token_ids: List of token IDs
            
        Returns:
            Dict mapping token_id -> price
        """
        try:
            response = self.client.get(
                f"{self.clob_url}/prices",
                params={"token_ids": ",".join(token_ids)}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch prices: {e}")
            return {}
    
    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Get midpoint price for a token."""
        try:
            response = self.client.get(
                f"{self.clob_url}/midpoint",
                params={"token_id": token_id}
            )
            response.raise_for_status()
            data = response.json()
            return float(data.get("mid", 0))
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch midpoint for {token_id}: {e}")
            return None
    
    def _parse_market(self, data: dict) -> Optional[Market]:
        """Parse raw API response into Market object."""
        try:
            # Extract outcomes - may be JSON string or list
            outcomes_raw = data.get("outcomes", '["Yes", "No"]')
            if isinstance(outcomes_raw, str):
                outcomes = json.loads(outcomes_raw)
            else:
                outcomes = outcomes_raw
            
            # Extract prices - may be JSON string or list
            prices_raw = data.get("outcomePrices", '["0.5", "0.5"]')
            if isinstance(prices_raw, str):
                prices_list = json.loads(prices_raw)
            else:
                prices_list = prices_raw
            
            # Convert prices to floats
            prices = [float(p) for p in prices_list]
            
            # Skip markets with no valid prices
            if not prices or len(prices) < 2:
                return None
            
            return Market(
                id=data.get("id", data.get("conditionId", "")),
                question=data.get("question", data.get("title", "Unknown")),
                slug=data.get("slug", ""),
                active=data.get("active", True),
                closed=data.get("closed", False),
                outcomes=outcomes,
                outcome_prices=prices,
                volume=float(data.get("volume", data.get("volumeNum", 0))),
                liquidity=float(data.get("liquidity", data.get("liquidityNum", 0))),
                end_date=data.get("endDate", data.get("endDateIso"))
            )
        except Exception as e:
            logger.warning(f"Failed to parse market: {e}")
            return None


# Create singleton instance
polymarket = PolymarketClient()


if __name__ == "__main__":
    # Quick test
    from rich import print as rprint
    
    client = PolymarketClient()
    markets = client.get_markets(limit=10)
    
    for market in markets:
        rprint(f"\n[bold]{market.question}[/bold]")
        rprint(f"  Outcomes: {market.outcomes}")
        rprint(f"  Prices: {market.outcome_prices}")
        rprint(f"  Total: {market.total_price:.4f}")
        rprint(f"  Arbitrage: {market.arbitrage_opportunity:.2f}%")
        if market.has_arbitrage:
            rprint(f"  [green]✅ ARBITRAGE OPPORTUNITY![/green]")

