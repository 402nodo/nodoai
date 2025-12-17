"""
Base class for prediction market platforms.
All platform integrations should inherit from this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class MarketCategory(Enum):
    """Categories for market classification."""
    POLITICS = "politics"
    CRYPTO = "crypto"
    SPORTS = "sports"
    ECONOMICS = "economics"
    ENTERTAINMENT = "entertainment"
    SCIENCE = "science"
    OTHER = "other"


@dataclass
class PlatformOutcome:
    """Represents a single outcome in a market."""
    name: str  # "Yes", "No", "Trump", etc.
    price: float  # 0.0 - 1.0
    token_id: Optional[str] = None  # Platform-specific token ID


@dataclass
class PlatformMarket:
    """
    Unified market representation across all platforms.
    This allows comparing markets from different platforms.
    """
    # Identification
    platform: str  # "polymarket", "kalshi", "azuro"
    market_id: str  # Platform-specific ID
    
    # Market info
    question: str  # "Will Trump win 2024?"
    description: str = ""
    slug: str = ""
    url: str = ""
    
    # Outcomes and prices
    outcomes: list[PlatformOutcome] = field(default_factory=list)
    
    # Metadata
    category: MarketCategory = MarketCategory.OTHER
    volume: float = 0.0
    liquidity: float = 0.0
    
    # Timing
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    # Status
    active: bool = True
    resolved: bool = False
    
    # For matching
    keywords: list[str] = field(default_factory=list)
    
    @property
    def total_price(self) -> float:
        """Sum of all outcome prices."""
        return sum(o.price for o in self.outcomes)
    
    @property
    def best_yes_price(self) -> Optional[float]:
        """Price of 'Yes' outcome if binary market."""
        for outcome in self.outcomes:
            if outcome.name.lower() in ["yes", "true"]:
                return outcome.price
        return self.outcomes[0].price if self.outcomes else None
    
    @property
    def best_no_price(self) -> Optional[float]:
        """Price of 'No' outcome if binary market."""
        for outcome in self.outcomes:
            if outcome.name.lower() in ["no", "false"]:
                return outcome.price
        return self.outcomes[1].price if len(self.outcomes) > 1 else None
    
    def get_outcome_price(self, outcome_name: str) -> Optional[float]:
        """Get price for a specific outcome."""
        for outcome in self.outcomes:
            if outcome.name.lower() == outcome_name.lower():
                return outcome.price
        return None
    
    def __repr__(self) -> str:
        prices = [f"{o.name}={o.price:.2%}" for o in self.outcomes]
        return f"<{self.platform}:{self.market_id} '{self.question[:30]}...' [{', '.join(prices)}]>"


class PredictionPlatform(ABC):
    """
    Abstract base class for prediction market platforms.
    Each platform integration must implement these methods.
    """
    
    name: str = "base"
    base_url: str = ""
    
    @abstractmethod
    def get_markets(self, limit: int = 100, **kwargs) -> list[PlatformMarket]:
        """
        Fetch active markets from the platform.
        
        Args:
            limit: Maximum number of markets to fetch
            **kwargs: Platform-specific filters
            
        Returns:
            List of PlatformMarket objects
        """
        pass
    
    @abstractmethod
    def get_market_by_id(self, market_id: str) -> Optional[PlatformMarket]:
        """
        Fetch a specific market by ID.
        
        Args:
            market_id: Platform-specific market ID
            
        Returns:
            PlatformMarket or None if not found
        """
        pass
    
    @abstractmethod
    def search_markets(self, query: str, limit: int = 20) -> list[PlatformMarket]:
        """
        Search markets by keyword.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching PlatformMarket objects
        """
        pass
    
    def get_market_url(self, market: PlatformMarket) -> str:
        """Get the URL to view this market on the platform."""
        return market.url or f"{self.base_url}/market/{market.market_id}"
    
    @property
    def is_decentralized(self) -> bool:
        """Whether this is a decentralized/crypto platform."""
        return False
    
    @property
    def trading_fee(self) -> float:
        """Platform trading fee as decimal (e.g., 0.02 = 2%)."""
        return 0.0

