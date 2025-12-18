"""
AI Analysis Endpoint
Multi-model consensus analysis for prediction markets.
"""
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from loguru import logger

from src.config import settings
from src.services.ai_orchestrator import AIOrchestrator, AnalysisTier


router = APIRouter()


# ==================
# Request/Response Models
# ==================

class AnalyzeRequest(BaseModel):
    """Request body for analysis."""
    market: str = Field(..., description="Market URL or ID (e.g., polymarket.com/event/btc-150k)")
    strategy: str = Field(default="yield_farming", description="Analysis strategy: yield_farming, delta_neutral, momentum")
    tier: str = Field(default="standard", description="Analysis tier: quick ($0.01), standard ($0.05), deep ($0.10)")


class AIModelResult(BaseModel):
    """Single AI model result."""
    name: str
    action: str
    confidence: int
    reasoning: Optional[str] = None


class MarketInfo(BaseModel):
    """Market information."""
    question: str
    yes_price: float
    no_price: float
    volume: Optional[float] = None
    end_date: Optional[str] = None
    url: str


class AnalysisResult(BaseModel):
    """Analysis consensus result."""
    consensus: str
    agreement: str
    confidence: int
    action: str
    potential_profit: Optional[str] = None
    apy: Optional[str] = None


class DissentInfo(BaseModel):
    """Dissenting model info."""
    model: str
    action: str
    reason: str


class AnalyzeResponse(BaseModel):
    """Response for analysis endpoint."""
    market: MarketInfo
    analysis: AnalysisResult
    models: List[AIModelResult]
    dissent: Optional[DissentInfo] = None
    risks: List[str]
    meta: dict


# ==================
# Endpoints
# ==================

@router.post("", response_model=AnalyzeResponse)
async def analyze_market(
    request: AnalyzeRequest = Body(...),
):
    """
    Analyze a prediction market using Multi-AI Consensus.
    
    Pricing:
    - Quick ($0.01): 1 AI model, ~2s
    - Standard ($0.05): 3 AI models, ~5s  
    - Deep ($0.10): 6 AI models, ~10s
    
    Payment: Include X-Payment-Tx header with Solana transaction signature
    """
    logger.info(f"Analyzing market: {request.market} (tier={request.tier})")
    
    try:
        # Get tier
        tier_map = {
            "quick": AnalysisTier.QUICK,
            "standard": AnalysisTier.STANDARD,
            "deep": AnalysisTier.DEEP,
        }
        tier = tier_map.get(request.tier, AnalysisTier.STANDARD)
        
        # Run analysis
        orchestrator = AIOrchestrator()
        result = await orchestrator.analyze(
            market_url=request.market,
            strategy=request.strategy,
            tier=tier
        )
        await orchestrator.close()
        
        # Build response
        return AnalyzeResponse(
            market=MarketInfo(
                question=result["market"]["question"],
                yes_price=result["market"]["yes_price"],
                no_price=result["market"]["no_price"],
                volume=result["market"].get("volume"),
                end_date=result["market"].get("end_date"),
                url=result["market"]["url"]
            ),
            analysis=AnalysisResult(
                consensus=result["consensus"]["action"],
                agreement=result["consensus"]["agreement"],
                confidence=result["consensus"]["confidence"],
                action=result["consensus"]["recommendation"],
                potential_profit=result["consensus"].get("profit_pct"),
                apy=result["consensus"].get("apy")
            ),
            models=[
                AIModelResult(
                    name=m["model"],
                    action=m["action"],
                    confidence=m["confidence"],
                    reasoning=m.get("reasoning")
                )
                for m in result["models"]
            ],
            dissent=DissentInfo(
                model=result["dissent"]["model"],
                action=result["dissent"]["action"],
                reason=result["dissent"]["reason"]
            ) if result.get("dissent") else None,
            risks=result.get("risks", []),
            meta={
                "request_id": result["meta"]["request_id"],
                "cost": f"${settings.get_price('analyze', request.tier):.2f}",
                "processing_time": result["meta"]["processing_time"],
                "models_used": result["meta"]["models_used"],
                "tier": request.tier
            }
        )
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiers")
async def get_analysis_tiers():
    """Get available analysis tiers and pricing."""
    return {
        "tiers": [
            {
                "name": "quick",
                "price": settings.price_ai_quick,
                "models": 1,
                "response_time": "~2s",
                "description": "Fast single-model analysis for quick checks"
            },
            {
                "name": "standard",
                "price": settings.price_ai_standard,
                "models": 3,
                "response_time": "~5s",
                "description": "Balanced multi-model analysis for normal use"
            },
            {
                "name": "deep",
                "price": settings.price_ai_deep,
                "models": 6,
                "response_time": "~10s",
                "description": "Full consensus with all models for important decisions"
            }
        ],
        "strategies": ["yield_farming", "delta_neutral", "momentum"]
    }


