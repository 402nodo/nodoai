"""
Nodo Bot Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Bot configuration from environment variables."""
    
    # Polymarket API
    POLYMARKET_API_URL: str = os.getenv("POLYMARKET_API_URL", "https://clob.polymarket.com")
    POLYMARKET_GAMMA_URL: str = "https://gamma-api.polymarket.com"
    
    # Wallet
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    
    # Arbitrage settings
    MIN_PROFIT_THRESHOLD: float = float(os.getenv("MIN_PROFIT_THRESHOLD", "0.5"))  # in %
    MAX_POSITION_SIZE: float = float(os.getenv("MAX_POSITION_SIZE", "1000"))  # in USDC
    SCAN_INTERVAL: int = int(os.getenv("SCAN_INTERVAL", "30"))  # in seconds
    
    # Fees (Polymarket fees)
    TRADING_FEE: float = 0.02  # 2% fee on winnings
    
    # Notifications
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        errors = []
        
        if not cls.PRIVATE_KEY:
            errors.append("PRIVATE_KEY is required")
        
        if cls.MIN_PROFIT_THRESHOLD < 0:
            errors.append("MIN_PROFIT_THRESHOLD must be >= 0")
        
        if cls.MAX_POSITION_SIZE <= 0:
            errors.append("MAX_POSITION_SIZE must be > 0")
        
        if errors:
            for error in errors:
                print(f"❌ Config Error: {error}")
            return False
        
        return True


# Create singleton instance
config = Config()

