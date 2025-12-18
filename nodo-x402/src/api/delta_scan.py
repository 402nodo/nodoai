"""
Delta Scanner Endpoint
Finds logical mispricing in related prediction markets.
"""
from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.config import settings
from src.services.delta_scanner import DeltaScanner


router = APIRouter()


# ==================
# Response Models
# ==================

class DeltaMarket(BaseModel):
    """Market info in delta opportunity."""
    question: str
    yes_price: float
    no_price: float
    url: str
    threshold: Optional[float] = None


class DeltaOpportunity(BaseModel):
    """A delta neutral / mispricing opportunity."""
    topic: str
    logic_error: str
    profit_potential: float
    confidence: int
    action: str
    explanation: str
    event_a: DeltaMarket
    event_b: DeltaMarket


class DeltaScanResponse(BaseModel):
    """Response for delta scan endpoint."""
    opportunities: List[DeltaOpportunity]
    total: int
    meta: dict


# ==================
# Endpoints
# ==================

@router.get("/scan", response_model=DeltaScanResponse)
async def scan_delta_opportunities(
    min_profit: float = Query(default=5.0, ge=0, description="Minimum profit potential (%)"),
    min_confidence: int = Query(default=50, ge=0, le=100, description="Minimum confidence score"),
    topic: Optional[str] = Query(default=None, description="Filter by topic (BTC, ETH, TRUMP, etc)"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
):
    """
    Scan for delta neutral / logical mispricing opportunities.
    
    Finds cases where related markets have inconsistent pricing:
    - BTC $150K YES > BTC $100K YES (impossible!)
    - YES + NO < $1.00 (free money)
    
    Price: $0.01 per request
    """
    logger.info(f"Delta scan: profit>{min_profit}%, conf>{min_confidence}")
    
    try:
        scanner = DeltaScanner()
        opportunities = await scanner.scan(limit=500)
        await scanner.close()
        
        # Filter
        filtered = []
        for opp in opportunities:
            if opp.profit_potential < min_profit:
                continue
            if opp.confidence < min_confidence:
                continue
            if topic and opp.topic.upper() != topic.upper():
                continue
            filtered.append(opp)
        
        # Limit
        filtered = filtered[:limit]
        
        return DeltaScanResponse(
            opportunities=[
                DeltaOpportunity(
                    topic=opp.topic,
                    logic_error=opp.logic_error,
                    profit_potential=opp.profit_potential,
                    confidence=opp.confidence,
                    action=opp.action,
                    explanation=opp.explanation,
                    event_a=DeltaMarket(
                        question=opp.event_a["question"],
                        yes_price=opp.event_a["yes_price"],
                        no_price=opp.event_a["no_price"],
                        url=opp.event_a["url"],
                        threshold=opp.event_a.get("threshold")
                    ),
                    event_b=DeltaMarket(
                        question=opp.event_b["question"],
                        yes_price=opp.event_b["yes_price"],
                        no_price=opp.event_b["no_price"],
                        url=opp.event_b["url"],
                        threshold=opp.event_b.get("threshold")
                    )
                )
                for opp in filtered
            ],
            total=len(filtered),
            meta={
                "price": f"${settings.price_delta_scan}",
                "filters": {
                    "min_profit": min_profit,
                    "min_confidence": min_confidence,
                    "topic": topic
                },
                "source": "polymarket"
            }
        )
        
    except Exception as e:
        logger.error(f"Delta scan error: {e}")
        return DeltaScanResponse(
            opportunities=[],
            total=0,
            meta={"error": str(e)}
        )


@router.get("/topics")
async def get_topics():
    """Get available topics for delta scanning."""
    return {
        "topics": [
            {"id": "BTC", "name": "Bitcoin", "category": "crypto"},
            {"id": "ETH", "name": "Ethereum", "category": "crypto"},
            {"id": "SOL", "name": "Solana", "category": "crypto"},
            {"id": "TRUMP", "name": "Trump", "category": "politics"},
            {"id": "FED_RATE", "name": "Fed Interest Rate", "category": "economy"},
            {"id": "SP500", "name": "S&P 500", "category": "stocks"},
        ]
    }


