"""
Webhooks Endpoint
Subscribe to real-time alerts for opportunities.
"""
from typing import Optional, List

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from loguru import logger

from src.config import settings


router = APIRouter()


# ==================
# Request/Response Models
# ==================

class WebhookCreateRequest(BaseModel):
    """Request to create a webhook subscription."""
    url: str = Field(..., description="Webhook URL to receive alerts")
    events: List[str] = Field(
        default=["opportunity.yield", "opportunity.delta"],
        description="Events to subscribe to"
    )
    filters: Optional[dict] = Field(
        default=None,
        description="Optional filters (e.g., min_profit, topics)"
    )


class WebhookResponse(BaseModel):
    """Webhook subscription response."""
    id: str
    url: str
    events: List[str]
    filters: Optional[dict]
    status: str
    created_at: str


class WebhookListResponse(BaseModel):
    """List of webhooks."""
    webhooks: List[WebhookResponse]
    total: int


# ==================
# Endpoints
# ==================

@router.post("", response_model=WebhookResponse)
async def create_webhook(
    request: WebhookCreateRequest = Body(...),
):
    """
    Create a webhook subscription for opportunity alerts.
    
    Events:
    - opportunity.yield - New yield farming opportunity
    - opportunity.delta - New delta/mispricing opportunity
    - opportunity.arbitrage - New arbitrage opportunity
    - market.resolved - Market has resolved
    
    Price: $0.005 per alert sent
    
    Webhook payload format:
    ```json
    {
      "event": "opportunity.yield",
      "data": {
        "question": "Will BTC reach $200K?",
        "outcome": "NO",
        "profit_pct": 3.5,
        "apy": 85.0,
        "url": "https://polymarket.com/..."
      },
      "timestamp": "2025-01-01T12:00:00Z"
    }
    ```
    """
    logger.info(f"Creating webhook: {request.url}")
    
    # Validate events
    valid_events = [
        "opportunity.yield",
        "opportunity.delta", 
        "opportunity.arbitrage",
        "market.resolved"
    ]
    
    for event in request.events:
        if event not in valid_events:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event: {event}. Valid events: {valid_events}"
            )
    
    # In production, store in database
    # For now, return mock response
    from datetime import datetime, timezone
    import uuid
    
    webhook_id = f"wh_{uuid.uuid4().hex[:12]}"
    
    return WebhookResponse(
        id=webhook_id,
        url=request.url,
        events=request.events,
        filters=request.filters,
        status="active",
        created_at=datetime.now(timezone.utc).isoformat()
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks():
    """
    List your webhook subscriptions.
    
    (Free - no payment required)
    """
    # In production, fetch from database based on auth
    return WebhookListResponse(
        webhooks=[],
        total=0
    )


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """
    Delete a webhook subscription.
    
    (Free - no payment required)
    """
    logger.info(f"Deleting webhook: {webhook_id}")
    
    # In production, delete from database
    return {"status": "deleted", "id": webhook_id}


@router.get("/events")
async def list_events():
    """Get available webhook events."""
    return {
        "events": [
            {
                "id": "opportunity.yield",
                "name": "Yield Opportunity",
                "description": "New high-probability yield farming opportunity",
                "price_per_alert": settings.price_webhook_alert
            },
            {
                "id": "opportunity.delta",
                "name": "Delta Opportunity", 
                "description": "New logical mispricing detected",
                "price_per_alert": settings.price_webhook_alert
            },
            {
                "id": "opportunity.arbitrage",
                "name": "Arbitrage Opportunity",
                "description": "New risk-free arbitrage opportunity",
                "price_per_alert": settings.price_webhook_alert
            },
            {
                "id": "market.resolved",
                "name": "Market Resolved",
                "description": "A watched market has resolved",
                "price_per_alert": settings.price_webhook_alert
            }
        ],
        "pricing": {
            "per_alert": f"${settings.price_webhook_alert}",
            "note": "Charged when alert is sent to your webhook"
        }
    }


