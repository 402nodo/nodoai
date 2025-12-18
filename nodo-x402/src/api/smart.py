"""
Smart Analyzer Endpoint
Category-specific deep analysis for prediction events.
"""
from typing import Optional, List

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from loguru import logger

from src.config import settings
from src.services.smart_analyzer import SmartAnalyzer, EventCategory


router = APIRouter()


# ==================
# Request/Response Models
# ==================

class SmartAnalyzeRequest(BaseModel):
    """Request for smart analysis."""
    question: str = Field(..., description="Event question text")
    current_price: float = Field(..., ge=0, le=1, description="Current market price (0-1)")
    outcome: str = Field(default="YES", description="Outcome to analyze (YES/NO)")
    days_left: int = Field(default=30, ge=0, description="Days until resolution")


class SmartAnalyzeResponse(BaseModel):
    """Response for smart analysis."""
    category: str
    confidence_score: int
    predicted_outcome: str
    verdict: str
    reasons: List[str]
    risks: List[str]
    data_used: dict
    meta: dict


# ==================
# Endpoints
# ==================

@router.post("/analyze", response_model=SmartAnalyzeResponse)
async def smart_analyze(
    request: SmartAnalyzeRequest = Body(...),
):
    """
    Smart category-specific analysis.
    
    Automatically detects event category (crypto, politics, tech, etc.)
    and applies specialized analysis logic.
    
    Price: $0.02 per request
    """
    logger.info(f"Smart analyze: {request.question[:50]}...")
    
    try:
        analyzer = SmartAnalyzer()
        result = analyzer.analyze(
            question=request.question,
            current_price=request.current_price,
            outcome=request.outcome,
            days_left=request.days_left
        )
        analyzer.close()
        
        return SmartAnalyzeResponse(
            category=result.category.value,
            confidence_score=result.confidence_score,
            predicted_outcome=result.predicted_outcome,
            verdict=result.verdict,
            reasons=result.reasons,
            risks=result.risks,
            data_used=result.data_used,
            meta={
                "price": f"${settings.price_smart_analyze}",
                "analyzer": "smart_v1"
            }
        )
        
    except Exception as e:
        logger.error(f"Smart analyze error: {e}")
        return SmartAnalyzeResponse(
            category="error",
            confidence_score=0,
            predicted_outcome=request.outcome,
            verdict=f"Analysis failed: {str(e)}",
            reasons=[],
            risks=["Analysis could not be completed"],
            data_used={},
            meta={"error": str(e)}
        )


@router.get("/categories")
async def get_categories():
    """Get supported event categories."""
    return {
        "categories": [
            {
                "id": "crypto_price",
                "name": "Cryptocurrency Price",
                "keywords": ["bitcoin", "btc", "ethereum", "eth", "crypto", "price", "reach"],
                "description": "Price targets for cryptocurrencies"
            },
            {
                "id": "politics",
                "name": "Politics",
                "keywords": ["president", "election", "trump", "biden", "resign", "impeach"],
                "description": "Political events and elections"
            },
            {
                "id": "tech",
                "name": "Technology",
                "keywords": ["spacex", "tesla", "ai", "launch", "release"],
                "description": "Tech company events and product launches"
            },
            {
                "id": "economy",
                "name": "Economy",
                "keywords": ["fed", "rate", "recession", "inflation", "gdp"],
                "description": "Economic indicators and Fed decisions"
            },
            {
                "id": "sports",
                "name": "Sports",
                "keywords": ["win", "championship", "nfl", "nba", "world cup"],
                "description": "Sports outcomes and championships"
            },
            {
                "id": "celebrity",
                "name": "Celebrity",
                "keywords": ["married", "pregnant", "arrested", "kardashian"],
                "description": "Celebrity news and events"
            }
        ]
    }


