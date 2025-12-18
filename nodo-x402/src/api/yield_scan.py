"""
Yield Scanner Endpoint
Finds high-probability events for yield farming strategy.
"""
from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.config import settings
from src.services.yield_scanner import YieldScanner


router = APIRouter()


# ==================
# Response Models
# ==================

class YieldOpportunity(BaseModel):
    """A yield farming opportunity."""
    market_id: str
    question: str
    outcome: str  # YES or NO
    buy_price: float
    profit_pct: float
    apy: float
    days_to_resolution: int
    volume: float
    risk_level: str  # LOW, MEDIUM, HIGH
    url: str


class YieldScanResponse(BaseModel):
    """Response for yield scan endpoint."""
    opportunities: List[YieldOpportunity]
    total: int
    filters: dict
    meta: dict


# ==================
# Endpoints
# ==================

@router.get("/scan", response_model=YieldScanResponse)
async def scan_yield_opportunities(
    min_probability: float = Query(default=0.95, ge=0.5, le=0.99, description="Minimum probability threshold"),
    min_volume: float = Query(default=5000, ge=0, description="Minimum market volume ($)"),
    max_days: int = Query(default=30, ge=1, le=365, description="Maximum days to resolution"),
    risk_level: Optional[str] = Query(default=None, description="Filter by risk: LOW, MEDIUM, HIGH"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results to return"),
):
    """
    Scan for yield farming opportunities.
    
    Finds prediction markets where one outcome has very high probability (95%+).
    Buy the likely outcome, wait for resolution, collect profit.
    
    Price: $0.005 per request
    """
    logger.info(f"Yield scan: prob>{min_probability}, vol>{min_volume}, days<{max_days}")
    
    try:
        scanner = YieldScanner(
            min_probability=min_probability,
            min_volume=min_volume,
            max_days=max_days
        )
        
        opportunities = scanner.scan(limit=limit * 2)  # Get more, filter later
        scanner.close()
        
        # Filter by risk level if specified
        if risk_level:
            opportunities = [o for o in opportunities if o.risk_level == risk_level.upper()]
        
        # Limit results
        opportunities = opportunities[:limit]
        
        return YieldScanResponse(
            opportunities=[
                YieldOpportunity(
                    market_id=o.market_id,
                    question=o.question,
                    outcome=o.outcome,
                    buy_price=o.buy_price,
                    profit_pct=o.profit_pct,
                    apy=o.apy,
                    days_to_resolution=o.days_to_resolution,
                    volume=o.volume,
                    risk_level=o.risk_level,
                    url=o.url
                )
                for o in opportunities
            ],
            total=len(opportunities),
            filters={
                "min_probability": min_probability,
                "min_volume": min_volume,
                "max_days": max_days,
                "risk_level": risk_level
            },
            meta={
                "price": f"${settings.price_yield_scan}",
                "source": "polymarket"
            }
        )
        
    except Exception as e:
        logger.error(f"Yield scan error: {e}")
        return YieldScanResponse(
            opportunities=[],
            total=0,
            filters={},
            meta={"error": str(e)}
        )


@router.get("/calculator")
async def calculate_yield(
    investment: float = Query(default=100, ge=1, description="Investment amount ($)"),
    min_probability: float = Query(default=0.95, ge=0.5, le=0.99),
    min_volume: float = Query(default=5000, ge=0),
    max_days: int = Query(default=30, ge=1, le=365),
    diversify: int = Query(default=5, ge=1, le=20, description="Number of markets to spread across"),
):
    """
    Calculate potential yield for an investment amount.
    
    Price: $0.005 per request
    """
    try:
        scanner = YieldScanner(
            min_probability=min_probability,
            min_volume=min_volume,
            max_days=max_days
        )
        
        opportunities = scanner.scan(limit=diversify * 2)
        scanner.close()
        
        if not opportunities:
            return {
                "investment": investment,
                "message": "No opportunities found with current filters"
            }
        
        # Take top N opportunities
        top_opps = opportunities[:diversify]
        per_market = investment / len(top_opps)
        
        positions = []
        total_expected_profit = 0
        
        for opp in top_opps:
            shares = per_market / opp.buy_price
            profit = shares * (1.0 - opp.buy_price)
            total_expected_profit += profit * (opp.buy_price)  # Weight by probability
            
            positions.append({
                "market": opp.question[:50],
                "outcome": opp.outcome,
                "investment": round(per_market, 2),
                "shares": round(shares, 2),
                "profit_if_wins": round(profit, 2),
                "probability": f"{opp.buy_price * 100:.1f}%",
                "apy": f"{opp.apy:.0f}%"
            })
        
        return {
            "investment": investment,
            "diversification": len(top_opps),
            "expected_profit": round(total_expected_profit, 2),
            "expected_return": f"{(total_expected_profit / investment) * 100:.1f}%",
            "positions": positions,
            "note": "Expected profit accounts for probability of each outcome"
        }
        
    except Exception as e:
        logger.error(f"Yield calculator error: {e}")
        return {"error": str(e)}


