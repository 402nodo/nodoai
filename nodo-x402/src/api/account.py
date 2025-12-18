"""
Account Endpoint
User account, balance, and usage statistics.
"""
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Header
from pydantic import BaseModel
from loguru import logger

from src.config import settings


router = APIRouter()


# ==================
# Response Models
# ==================

class BalanceResponse(BaseModel):
    """Account balance response."""
    wallet_address: Optional[str]
    balance_usd: float
    currency: str = "USDC"
    requests_available: dict


class UsageResponse(BaseModel):
    """Usage statistics response."""
    period: str
    total_spent: float
    total_requests: int
    by_endpoint: dict
    by_tier: Optional[dict] = None
    daily_breakdown: Optional[List[dict]] = None


class TopUpResponse(BaseModel):
    """Top-up instructions response."""
    recipient: str
    network: str
    currency: str
    usdc_mint: str
    instructions: str


# ==================
# Endpoints
# ==================

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    x_wallet_address: Optional[str] = Header(default=None, alias="X-Wallet-Address"),
):
    """
    Get account balance and available requests.
    
    (Free - no payment required)
    
    Note: x402 is pay-per-request, so "balance" reflects your wallet's USDC balance.
    """
    # In production, check actual wallet balance on Solana
    # For now, return informational response
    
    return BalanceResponse(
        wallet_address=x_wallet_address,
        balance_usd=0.0,  # Would check actual USDC balance
        currency="USDC",
        requests_available={
            "ai_quick": "Pay $0.01 per request",
            "ai_standard": "Pay $0.05 per request",
            "ai_deep": "Pay $0.10 per request",
            "yield_scan": "Pay $0.005 per request",
            "delta_scan": "Pay $0.01 per request",
            "note": "x402 is pay-per-request - no prepaid balance needed"
        }
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    period: str = Query(default=None, description="Period in YYYY-MM format"),
    x_wallet_address: Optional[str] = Header(default=None, alias="X-Wallet-Address"),
):
    """
    Get usage statistics for your account.
    
    (Free - no payment required)
    """
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
    
    # In production, fetch from database
    # For now, return empty usage
    
    return UsageResponse(
        period=period,
        total_spent=0.0,
        total_requests=0,
        by_endpoint={
            "analyze": {"count": 0, "spent": 0.0},
            "yield_scan": {"count": 0, "spent": 0.0},
            "delta_scan": {"count": 0, "spent": 0.0},
            "smart_analyze": {"count": 0, "spent": 0.0},
            "arbitrage_scan": {"count": 0, "spent": 0.0},
            "markets": {"count": 0, "spent": 0.0},
        },
        by_tier={
            "quick": {"count": 0, "spent": 0.0},
            "standard": {"count": 0, "spent": 0.0},
            "deep": {"count": 0, "spent": 0.0},
        },
        daily_breakdown=[]
    )


@router.get("/topup", response_model=TopUpResponse)
async def get_topup_instructions():
    """
    Get instructions for funding your account.
    
    x402 uses pay-per-request model - simply have USDC in your Solana wallet.
    
    (Free - no payment required)
    """
    return TopUpResponse(
        recipient=settings.nodo_wallet_address or "Configure NODO_WALLET_ADDRESS",
        network="solana-mainnet",
        currency="USDC",
        usdc_mint=settings.solana_usdc_mint,
        instructions="""
x402 is pay-per-request. You don't need to "top up" - just:

1. Have USDC in your Solana wallet
2. Make a request to any paid endpoint
3. Receive 402 Payment Required with payment details
4. Send USDC payment to the specified address
5. Retry request with X-Payment-Tx header containing your transaction signature
6. Receive response!

Your wallet is never locked or custodied. Pay only for what you use.
        """.strip()
    )


@router.get("/pricing")
async def get_pricing():
    """Get current pricing for all endpoints."""
    return {
        "pricing": {
            "ai_analysis": {
                "quick": {"price": settings.price_ai_quick, "models": 1, "time": "~2s"},
                "standard": {"price": settings.price_ai_standard, "models": 3, "time": "~5s"},
                "deep": {"price": settings.price_ai_deep, "models": 6, "time": "~10s"},
            },
            "scanners": {
                "yield_scan": settings.price_yield_scan,
                "delta_scan": settings.price_delta_scan,
                "smart_analyze": settings.price_smart_analyze,
                "arbitrage_scan": settings.price_arbitrage_scan,
            },
            "data": {
                "markets": settings.price_market_data,
            },
            "webhooks": {
                "per_alert": settings.price_webhook_alert,
            }
        },
        "currency": "USDC",
        "network": "solana-mainnet",
        "volume_discounts": {
            "$10-50/month": "10% off",
            "$50-100/month": "15% off",
            "$100+/month": "20% off",
        }
    }


