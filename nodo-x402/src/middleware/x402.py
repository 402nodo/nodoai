"""
x402 Payment Required Middleware for Solana
Implements HTTP 402 Payment Required protocol using Solana USDC.
"""
import time
import uuid
from typing import Optional, Callable
from datetime import datetime, timezone, timedelta

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from src.config import settings


class X402Middleware(BaseHTTPMiddleware):
    """
    x402 Payment Required middleware.
    
    Intercepts requests to paid endpoints and:
    1. Checks for payment proof header (X-Payment-Signature)
    2. If no payment, returns 402 with payment instructions
    3. If payment exists, verifies on Solana and proceeds
    """
    
    # Endpoints that require payment
    PAID_ENDPOINTS = {
        "/analyze": lambda r: settings.get_price("analyze", r.query_params.get("tier", "standard")),
        "/yield/scan": lambda r: settings.price_yield_scan,
        "/delta/scan": lambda r: settings.price_delta_scan,
        "/smart/analyze": lambda r: settings.price_smart_analyze,
        "/arbitrage/scan": lambda r: settings.price_arbitrage_scan,
        "/markets": lambda r: settings.price_market_data,
        "/webhooks": lambda r: settings.price_webhook_alert,
    }
    
    # Endpoints that don't require payment
    FREE_ENDPOINTS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/x402/info",
        "/account/balance",
        "/account/usage",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through x402 payment flow."""
        
        path = request.url.path
        
        # Skip free endpoints
        if path in self.FREE_ENDPOINTS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)
        
        # Check if this is a paid endpoint
        price_func = None
        for endpoint, func in self.PAID_ENDPOINTS.items():
            if path.startswith(endpoint):
                price_func = func
                break
        
        if not price_func:
            return await call_next(request)
        
        # Get required payment amount
        amount = price_func(request)
        
        # Check for payment proof in headers
        payment_signature = request.headers.get("X-Payment-Signature")
        payment_tx = request.headers.get("X-Payment-Tx")
        
        if payment_signature or payment_tx:
            # Verify payment
            verified = await self._verify_payment(
                request, 
                payment_signature or payment_tx, 
                amount
            )
            
            if verified:
                # Payment verified, proceed with request
                logger.info(f"Payment verified: {payment_tx[:16]}... for {path}")
                return await call_next(request)
            else:
                # Invalid payment
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": {
                            "code": "PAYMENT_INVALID",
                            "message": "Payment verification failed"
                        }
                    }
                )
        
        # No payment - return 402 Payment Required
        return self._create_402_response(request, amount, path)
    
    def _create_402_response(
        self, 
        request: Request, 
        amount: float, 
        endpoint: str
    ) -> JSONResponse:
        """Create 402 Payment Required response with Solana payment details."""
        
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.payment_confirmation_timeout
        )
        
        response_data = {
            "error": {
                "code": "PAYMENT_REQUIRED",
                "message": f"This request requires payment of ${amount:.4f} USDC"
            },
            "payment": {
                "x402_version": 1,
                "network": "solana-mainnet",
                "amount": f"{amount:.6f}",
                "currency": "USDC",
                "decimals": 6,
                "recipient": settings.nodo_wallet_address,
                "usdc_mint": settings.solana_usdc_mint,
                "memo": request_id,
                "expires_at": expires_at.isoformat(),
                "instructions": {
                    "description": f"Send {amount} USDC to the recipient address with memo '{request_id}'",
                    "steps": [
                        "1. Send USDC SPL token transfer to recipient",
                        f"2. Include memo: {request_id}",
                        "3. Retry request with X-Payment-Tx header containing transaction signature"
                    ]
                }
            },
            "request": {
                "id": request_id,
                "endpoint": endpoint,
                "method": request.method,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        return JSONResponse(
            status_code=402,
            content=response_data,
            headers={
                "X-Payment-Required": "true",
                "X-Payment-Amount": str(amount),
                "X-Payment-Currency": "USDC",
                "X-Payment-Network": "solana",
                "X-Payment-Recipient": settings.nodo_wallet_address,
            }
        )
    
    async def _verify_payment(
        self, 
        request: Request, 
        tx_signature: str, 
        expected_amount: float
    ) -> bool:
        """
        Verify payment on Solana blockchain.
        
        Args:
            request: The incoming request
            tx_signature: Solana transaction signature
            expected_amount: Expected payment amount in USDC
            
        Returns:
            True if payment is valid
        """
        try:
            # Get Solana client from app state
            if not hasattr(request.app.state, 'solana_client'):
                logger.error("Solana client not initialized")
                return False
            
            solana_client = request.app.state.solana_client
            
            # Verify the transaction
            result = await solana_client.verify_usdc_transfer(
                tx_signature=tx_signature,
                expected_recipient=settings.nodo_wallet_address,
                expected_amount=expected_amount,
                usdc_mint=settings.solana_usdc_mint
            )
            
            return result.get("valid", False)
            
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            return False


class X402PaymentRequired(Exception):
    """Exception raised when payment is required."""
    
    def __init__(self, amount: float, endpoint: str, request_id: str = None):
        self.amount = amount
        self.endpoint = endpoint
        self.request_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        super().__init__(f"Payment of ${amount} USDC required for {endpoint}")


