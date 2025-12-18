"""
Arbitrage Scanner Endpoint
Finds intra-platform arbitrage opportunities.
"""
from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

from src.config import settings
from src.services.arbitrage_scanner import ArbitrageScanner


router = APIRouter()


# ==================
# Response Models
# ==================

class ArbitrageOpportunity(BaseModel):
    """An arbitrage opportunity."""
    market_question: str
    yes_price: float
    no_price: float
    total_cost: float
    guaranteed_profit: float
    profit_pct: float
    volume: float
    url: str


class ArbitrageScanResponse(BaseModel):
    """Response for arbitrage scan."""
    opportunities: List[ArbitrageOpportunity]
    total: int
    meta: dict


# ==================
# Endpoints
# ==================

@router.get("/scan", response_model=ArbitrageScanResponse)
async def scan_arbitrage(
    min_profit: float = Query(default=0.5, ge=0, description="Minimum profit (%)"),
    min_volume: float = Query(default=1000, ge=0, description="Minimum market volume ($)"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Scan for intra-platform arbitrage opportunities.
    
    Finds markets where YES + NO < $1.00, allowing risk-free profit
    by buying both outcomes.
    
    Price: $0.01 per request
    """
    logger.info(f"Arbitrage scan: profit>{min_profit}%, vol>{min_volume}")
    
    try:
        scanner = ArbitrageScanner()
        opportunities = scanner.scan(limit=limit * 3)
        scanner.close()
        
        # Filter
        filtered = []
        for opp in opportunities:
            if opp.net_profit_pct < min_profit:
                continue
            if opp.market.volume < min_volume:
                continue
            
            filtered.append(ArbitrageOpportunity(
                market_question=opp.market.question,
                yes_price=opp.market.yes_price,
                no_price=opp.market.no_price,
                total_cost=opp.total_cost,
                guaranteed_profit=opp.guaranteed_profit,
                profit_pct=opp.net_profit_pct,
                volume=opp.market.volume,
                url=opp.market.url
            ))
        
        return ArbitrageScanResponse(
            opportunities=filtered[:limit],
            total=len(filtered),
            meta={
                "price": f"${settings.price_arbitrage_scan}",
                "filters": {
                    "min_profit": min_profit,
                    "min_volume": min_volume
                },
                "source": "polymarket"
            }
        )
        
    except Exception as e:
        logger.error(f"Arbitrage scan error: {e}")
        return ArbitrageScanResponse(
            opportunities=[],
            total=0,
            meta={"error": str(e)}
        )


