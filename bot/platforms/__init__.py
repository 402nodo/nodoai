"""
Prediction Market Platform Integrations
"""
from .base import PredictionPlatform, PlatformMarket, PlatformOutcome, MarketCategory
from .polymarket import PolymarketPlatform
from .kalshi import KalshiPlatform
from .azuro import AzuroPlatform
from .predictit import PredictItPlatform

__all__ = [
    "PredictionPlatform",
    "PlatformMarket", 
    "PlatformOutcome",
    "MarketCategory",
    "PolymarketPlatform",
    "KalshiPlatform",
    "AzuroPlatform",
    "PredictItPlatform",
]

