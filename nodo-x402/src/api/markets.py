"""
Market Data Endpoint
Raw market data from prediction platforms.
"""
from typing import Optional, List

from fastapi import APIRouter, Query, Path
from pydantic import BaseModel
from loguru import logger

from src.config import settings
from src.services.market_data import MarketDataService


router = APIRouter()


# ==================
# Response Models
# ==================

class Market(BaseModel):
    """Market data."""
    id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: Optional[float] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    platform: str
    url: str


class MarketsResponse(BaseModel):
    """Response for markets list."""
    markets: List[Market]
    total: int
    meta: dict


class MarketDetailResponse(BaseModel):
    """Detailed market info."""
    market: Market
    orderbook: Optional[dict] = None
    history: Optional[List[dict]] = None
    meta: dict


# ==================
# Endpoints
# ==================

@router.get("", response_model=MarketsResponse)
async def list_markets(
    platform: str = Query(default="polymarket", description="Platform: polymarket, kalshi"),
    active: bool = Query(default=True, description="Only active markets"),
    min_volume: float = Query(default=0, ge=0, description="Minimum volume ($)"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    search: Optional[str] = Query(default=None, description="Search in question text"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List markets from prediction platforms.
    
    Price: $0.001 per request
    """
    logger.info(f"Markets list: platform={platform}, limit={limit}")
    
    try:
        service = MarketDataService()
        markets = await service.get_markets(
            platform=platform,
            active=active,
            min_volume=min_volume,
            category=category,
            search=search,
            limit=limit,
            offset=offset
        )
        await service.close()
        
        return MarketsResponse(
            markets=[
                Market(
                    id=m["id"],
                    question=m["question"],
                    yes_price=m["yes_price"],
                    no_price=m["no_price"],
                    volume=m["volume"],
                    liquidity=m.get("liquidity"),
                    end_date=m.get("end_date"),
                    category=m.get("category"),
                    platform=platform,
                    url=m["url"]
                )
                for m in markets
            ],
            total=len(markets),
            meta={
                "price": f"${settings.price_market_data}",
                "platform": platform,
                "filters": {
                    "active": active,
                    "min_volume": min_volume,
                    "category": category,
                    "search": search
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Markets list error: {e}")
        return MarketsResponse(
            markets=[],
            total=0,
            meta={"error": str(e)}
        )


@router.get("/{market_id}", response_model=MarketDetailResponse)
async def get_market(
    market_id: str = Path(..., description="Market ID"),
    platform: str = Query(default="polymarket"),
    include_orderbook: bool = Query(default=False),
    include_history: bool = Query(default=False),
):
    """
    Get detailed market information.
    
    Price: $0.001 per request
    """
    logger.info(f"Market detail: {market_id}")
    
    try:
        service = MarketDataService()
        market = await service.get_market(
            platform=platform,
            market_id=market_id,
            include_orderbook=include_orderbook,
            include_history=include_history
        )
        await service.close()
        
        if not market:
            return MarketDetailResponse(
                market=None,
                meta={"error": "Market not found"}
            )
        
        return MarketDetailResponse(
            market=Market(
                id=market["id"],
                question=market["question"],
                yes_price=market["yes_price"],
                no_price=market["no_price"],
                volume=market["volume"],
                liquidity=market.get("liquidity"),
                end_date=market.get("end_date"),
                category=market.get("category"),
                platform=platform,
                url=market["url"]
            ),
            orderbook=market.get("orderbook"),
            history=market.get("history"),
            meta={
                "price": f"${settings.price_market_data}",
                "platform": platform
            }
        )
        
    except Exception as e:
        logger.error(f"Market detail error: {e}")
        return MarketDetailResponse(
            market=None,
            meta={"error": str(e)}
        )


@router.get("/platforms/supported")
async def get_platforms():
    """Get supported prediction platforms."""
    return {
        "platforms": [
            {
                "id": "polymarket",
                "name": "Polymarket",
                "status": "live",
                "features": ["markets", "orderbook", "history"]
            },
            {
                "id": "kalshi",
                "name": "Kalshi",
                "status": "live",
                "features": ["markets", "orderbook"]
            },
            {
                "id": "azuro",
                "name": "Azuro",
                "status": "beta",
                "features": ["markets"]
            },
            {
                "id": "predictit",
                "name": "PredictIt",
                "status": "planned",
                "features": []
            }
        ]
    }


