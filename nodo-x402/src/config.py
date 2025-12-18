"""
NODO x402 Configuration
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ===================
    # Solana Configuration
    # ===================
    solana_rpc_url: str = Field(
        default="https://api.mainnet-beta.solana.com",
        description="Solana RPC endpoint"
    )
    solana_ws_url: str = Field(
        default="wss://api.mainnet-beta.solana.com",
        description="Solana WebSocket endpoint"
    )
    solana_usdc_mint: str = Field(
        default="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        description="USDC SPL Token mint address on Solana"
    )
    nodo_wallet_address: str = Field(
        default="",
        description="NODO payment receiving wallet"
    )
    nodo_private_key: str = Field(
        default="",
        description="NODO wallet private key for verification"
    )
    payment_confirmation_timeout: int = Field(
        default=30,
        description="Seconds to wait for payment confirmation"
    )
    payment_required_confirmations: int = Field(
        default=1,
        description="Required confirmations for payment"
    )
    
    # ===================
    # AI API Keys
    # ===================
    openrouter_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    google_api_key: str = Field(default="")
    
    # ===================
    # Database
    # ===================
    database_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/nodo_x402"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # ===================
    # Server
    # ===================
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    cors_origins: str = Field(default="*")
    rate_limit_per_minute: int = Field(default=60)
    
    # ===================
    # Pricing (in USDC)
    # ===================
    price_ai_quick: float = Field(default=0.01)
    price_ai_standard: float = Field(default=0.05)
    price_ai_deep: float = Field(default=0.10)
    price_yield_scan: float = Field(default=0.005)
    price_delta_scan: float = Field(default=0.01)
    price_smart_analyze: float = Field(default=0.02)
    price_arbitrage_scan: float = Field(default=0.01)
    price_market_data: float = Field(default=0.001)
    price_webhook_alert: float = Field(default=0.005)
    
    # ===================
    # External APIs
    # ===================
    polymarket_api_url: str = Field(
        default="https://gamma-api.polymarket.com"
    )
    kalshi_api_url: str = Field(
        default="https://trading-api.kalshi.com"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def get_price(self, endpoint: str, tier: str = None) -> float:
        """Get price for an endpoint."""
        prices = {
            "analyze": {
                "quick": self.price_ai_quick,
                "standard": self.price_ai_standard,
                "deep": self.price_ai_deep,
            },
            "yield_scan": self.price_yield_scan,
            "delta_scan": self.price_delta_scan,
            "smart_analyze": self.price_smart_analyze,
            "arbitrage_scan": self.price_arbitrage_scan,
            "market_data": self.price_market_data,
            "webhook": self.price_webhook_alert,
        }
        
        if endpoint == "analyze" and tier:
            return prices["analyze"].get(tier, self.price_ai_standard)
        
        return prices.get(endpoint, 0.01)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience instance
settings = get_settings()


