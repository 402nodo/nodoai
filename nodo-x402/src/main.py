"""
NODO x402 - Main FastAPI Application
Solana-native micropayments for AI prediction market analysis.
"""
import sys
from contextlib import asynccontextmanager
from loguru import logger

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.api import analyze, yield_scan, delta_scan, smart, arbitrage, markets, webhooks, account
from src.middleware.x402 import X402Middleware
from src.solana.client import SolanaPaymentClient


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting NODO x402 Server...")
    logger.info(f"   Solana RPC: {settings.solana_rpc_url}")
    logger.info(f"   USDC Mint: {settings.solana_usdc_mint}")
    logger.info(f"   Payment Wallet: {settings.nodo_wallet_address[:8]}..." if settings.nodo_wallet_address else "   ⚠️  No payment wallet configured!")
    
    # Initialize Solana client
    app.state.solana_client = SolanaPaymentClient()
    await app.state.solana_client.connect()
    
    logger.info("✅ NODO x402 Server ready!")
    
    yield
    
    # Cleanup
    logger.info("Shutting down NODO x402 Server...")
    await app.state.solana_client.close()


# Create FastAPI app
app = FastAPI(
    title="NODO x402 API",
    description="AI-powered prediction market analysis with Solana micropayments (x402 protocol)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# x402 Payment middleware
app.add_middleware(X402Middleware)


# ==================
# Health & Info
# ==================

@app.get("/", tags=["info"])
async def root():
    """API root - basic info."""
    return {
        "service": "NODO x402 API",
        "version": "1.0.0",
        "protocol": "x402",
        "network": "solana-mainnet",
        "docs": "/docs",
        "pricing": {
            "ai_analysis": {
                "quick": f"${settings.price_ai_quick}",
                "standard": f"${settings.price_ai_standard}",
                "deep": f"${settings.price_ai_deep}",
            },
            "yield_scan": f"${settings.price_yield_scan}",
            "delta_scan": f"${settings.price_delta_scan}",
            "smart_analyze": f"${settings.price_smart_analyze}",
            "arbitrage_scan": f"${settings.price_arbitrage_scan}",
            "market_data": f"${settings.price_market_data}",
        }
    }


@app.get("/health", tags=["info"])
async def health_check(request: Request):
    """Health check endpoint."""
    solana_connected = False
    try:
        if hasattr(request.app.state, 'solana_client'):
            solana_connected = await request.app.state.solana_client.is_connected()
    except:
        pass
    
    return {
        "status": "healthy",
        "solana_connected": solana_connected,
        "version": "1.0.0"
    }


@app.get("/x402/info", tags=["x402"])
async def x402_info():
    """x402 protocol information."""
    return {
        "x402_version": 1,
        "network": "solana-mainnet",
        "currency": "USDC",
        "recipient": settings.nodo_wallet_address,
        "usdc_mint": settings.solana_usdc_mint,
        "confirmation_timeout": settings.payment_confirmation_timeout,
        "supported_endpoints": [
            {"path": "/analyze", "methods": ["POST"], "price_range": "$0.01 - $0.10"},
            {"path": "/yield/scan", "methods": ["GET"], "price": "$0.005"},
            {"path": "/delta/scan", "methods": ["GET"], "price": "$0.01"},
            {"path": "/smart/analyze", "methods": ["POST"], "price": "$0.02"},
            {"path": "/arbitrage/scan", "methods": ["GET"], "price": "$0.01"},
            {"path": "/markets", "methods": ["GET"], "price": "$0.001"},
            {"path": "/webhooks", "methods": ["POST"], "price": "$0.005/alert"},
        ]
    }


# ==================
# Include Routers
# ==================

app.include_router(analyze.router, prefix="/analyze", tags=["AI Analysis"])
app.include_router(yield_scan.router, prefix="/yield", tags=["Yield Scanner"])
app.include_router(delta_scan.router, prefix="/delta", tags=["Delta Scanner"])
app.include_router(smart.router, prefix="/smart", tags=["Smart Analyzer"])
app.include_router(arbitrage.router, prefix="/arbitrage", tags=["Arbitrage Scanner"])
app.include_router(markets.router, prefix="/markets", tags=["Market Data"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(account.router, prefix="/account", tags=["Account"])


# ==================
# Error Handlers
# ==================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )


# ==================
# Run Server
# ==================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )


