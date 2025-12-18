"""
NODO x402 Client
Handles API requests with automatic Solana USDC payments.
"""
import json
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

import httpx

from .models import AnalysisResult, YieldOpportunity, DeltaOpportunity, Market
from .exceptions import PaymentRequired, PaymentFailed, APIError
from .solana import SolanaWallet


class NodoClient:
    """
    NODO x402 API Client with automatic payment handling.
    
    Example:
        ```python
        from nodo_x402 import NodoClient
        
        client = NodoClient(keypair_path="~/.config/solana/id.json")
        
        # Analyze a market - auto-pays via x402
        result = await client.analyze(
            market="polymarket.com/event/btc-150k",
            tier="deep"
        )
        
        print(f"Consensus: {result.consensus}")
        ```
    """
    
    DEFAULT_BASE_URL = "https://api.nodo.ai/x402/v1"
    
    def __init__(
        self,
        keypair_path: Optional[str] = None,
        private_key: Optional[bytes] = None,
        base_url: str = None,
        auto_pay: bool = True,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
    ):
        """
        Initialize NODO client.
        
        Args:
            keypair_path: Path to Solana keypair JSON file
            private_key: Solana private key bytes (alternative to keypair_path)
            base_url: API base URL (defaults to production)
            auto_pay: Automatically handle 402 payments (default True)
            rpc_url: Solana RPC endpoint
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.auto_pay = auto_pay
        
        # Initialize Solana wallet
        self.wallet = SolanaWallet(
            keypair_path=keypair_path,
            private_key=private_key,
            rpc_url=rpc_url,
        )
        
        # HTTP client
        self._client = httpx.AsyncClient(timeout=60.0)
    
    # ==================
    # AI Analysis
    # ==================
    
    async def analyze(
        self,
        market: str,
        tier: str = "standard",
        strategy: str = "yield_farming",
    ) -> AnalysisResult:
        """
        Analyze a prediction market using Multi-AI Consensus.
        
        Args:
            market: Market URL or ID
            tier: Analysis tier (quick=$0.01, standard=$0.05, deep=$0.10)
            strategy: Analysis strategy (yield_farming, delta_neutral, momentum)
            
        Returns:
            AnalysisResult with consensus, models, and risks
        """
        data = await self._request(
            "POST",
            "/analyze",
            json={
                "market": market,
                "tier": tier,
                "strategy": strategy,
            }
        )
        return AnalysisResult.from_dict(data)
    
    # ==================
    # Scanners
    # ==================
    
    async def yield_scan(
        self,
        min_probability: float = 0.95,
        min_volume: float = 5000,
        max_days: int = 30,
        risk_level: Optional[str] = None,
        limit: int = 20,
    ) -> List[YieldOpportunity]:
        """
        Scan for yield farming opportunities.
        
        Args:
            min_probability: Minimum outcome probability (0.9-0.99)
            min_volume: Minimum market volume ($)
            max_days: Maximum days to resolution
            risk_level: Filter by risk (LOW, MEDIUM, HIGH)
            limit: Maximum results
            
        Returns:
            List of yield opportunities sorted by APY
        """
        params = {
            "min_probability": min_probability,
            "min_volume": min_volume,
            "max_days": max_days,
            "limit": limit,
        }
        if risk_level:
            params["risk_level"] = risk_level
        
        data = await self._request("GET", "/yield/scan", params=params)
        return [YieldOpportunity.from_dict(o) for o in data.get("opportunities", [])]
    
    async def delta_scan(
        self,
        min_profit: float = 5.0,
        min_confidence: int = 50,
        topic: Optional[str] = None,
        limit: int = 20,
    ) -> List[DeltaOpportunity]:
        """
        Scan for delta neutral / mispricing opportunities.
        
        Args:
            min_profit: Minimum profit potential (%)
            min_confidence: Minimum confidence score
            topic: Filter by topic (BTC, ETH, TRUMP, etc)
            limit: Maximum results
            
        Returns:
            List of mispricing opportunities
        """
        params = {
            "min_profit": min_profit,
            "min_confidence": min_confidence,
            "limit": limit,
        }
        if topic:
            params["topic"] = topic
        
        data = await self._request("GET", "/delta/scan", params=params)
        return [DeltaOpportunity.from_dict(o) for o in data.get("opportunities", [])]
    
    async def arbitrage_scan(
        self,
        min_profit: float = 0.5,
        min_volume: float = 1000,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Scan for intra-platform arbitrage opportunities.
        
        Args:
            min_profit: Minimum profit (%)
            min_volume: Minimum volume ($)
            limit: Maximum results
            
        Returns:
            List of arbitrage opportunities
        """
        data = await self._request(
            "GET",
            "/arbitrage/scan",
            params={
                "min_profit": min_profit,
                "min_volume": min_volume,
                "limit": limit,
            }
        )
        return data.get("opportunities", [])
    
    async def smart_analyze(
        self,
        question: str,
        current_price: float,
        outcome: str = "YES",
        days_left: int = 30,
    ) -> Dict:
        """
        Smart category-specific analysis.
        
        Args:
            question: Event question text
            current_price: Current market price (0-1)
            outcome: Outcome to analyze (YES/NO)
            days_left: Days until resolution
            
        Returns:
            Smart analysis result
        """
        return await self._request(
            "POST",
            "/smart/analyze",
            json={
                "question": question,
                "current_price": current_price,
                "outcome": outcome,
                "days_left": days_left,
            }
        )
    
    # ==================
    # Market Data
    # ==================
    
    async def get_markets(
        self,
        platform: str = "polymarket",
        active: bool = True,
        min_volume: float = 0,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> List[Market]:
        """
        Get list of markets from prediction platforms.
        
        Args:
            platform: Platform (polymarket, kalshi)
            active: Only active markets
            min_volume: Minimum volume ($)
            search: Search in question text
            limit: Maximum results
            
        Returns:
            List of markets
        """
        params = {
            "platform": platform,
            "active": active,
            "min_volume": min_volume,
            "limit": limit,
        }
        if search:
            params["search"] = search
        
        data = await self._request("GET", "/markets", params=params)
        return [Market.from_dict(m) for m in data.get("markets", [])]
    
    async def get_market(
        self,
        market_id: str,
        platform: str = "polymarket",
    ) -> Optional[Market]:
        """Get detailed market info."""
        data = await self._request(
            "GET",
            f"/markets/{market_id}",
            params={"platform": platform}
        )
        if data.get("market"):
            return Market.from_dict(data["market"])
        return None
    
    # ==================
    # Account
    # ==================
    
    async def get_usage(self, period: Optional[str] = None) -> Dict:
        """Get usage statistics."""
        params = {}
        if period:
            params["period"] = period
        return await self._request("GET", "/account/usage", params=params)
    
    async def get_pricing(self) -> Dict:
        """Get current API pricing."""
        return await self._request("GET", "/account/pricing")
    
    # ==================
    # Webhooks
    # ==================
    
    async def create_webhook(
        self,
        url: str,
        events: List[str] = None,
        filters: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a webhook subscription.
        
        Args:
            url: Webhook URL
            events: Events to subscribe to
            filters: Optional filters
            
        Returns:
            Webhook subscription info
        """
        if events is None:
            events = ["opportunity.yield", "opportunity.delta"]
        
        return await self._request(
            "POST",
            "/webhooks",
            json={
                "url": url,
                "events": events,
                "filters": filters,
            }
        )
    
    async def list_webhooks(self) -> List[Dict]:
        """List your webhook subscriptions."""
        data = await self._request("GET", "/webhooks")
        return data.get("webhooks", [])
    
    async def delete_webhook(self, webhook_id: str) -> Dict:
        """Delete a webhook subscription."""
        return await self._request("DELETE", f"/webhooks/{webhook_id}")
    
    # ==================
    # Internal Methods
    # ==================
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Dict = None,
        json: Dict = None,
        headers: Dict = None,
    ) -> Dict:
        """Make API request with automatic payment handling."""
        url = f"{self.base_url}{path}"
        req_headers = headers or {}
        
        # Add wallet address header
        if self.wallet.address:
            req_headers["X-Wallet-Address"] = self.wallet.address
        
        # Make initial request
        response = await self._client.request(
            method,
            url,
            params=params,
            json=json,
            headers=req_headers,
        )
        
        # Handle 402 Payment Required
        if response.status_code == 402:
            if not self.auto_pay:
                data = response.json()
                raise PaymentRequired(
                    amount=float(data["payment"]["amount"]),
                    recipient=data["payment"]["recipient"],
                    memo=data["payment"]["memo"],
                )
            
            # Auto-pay
            payment_data = response.json()["payment"]
            tx_signature = await self._handle_payment(payment_data)
            
            # Retry with payment proof
            req_headers["X-Payment-Tx"] = tx_signature
            response = await self._client.request(
                method,
                url,
                params=params,
                json=json,
                headers=req_headers,
            )
        
        # Handle errors
        if response.status_code >= 400:
            raise APIError(response.status_code, response.text)
        
        return response.json()
    
    async def _handle_payment(self, payment_data: Dict) -> str:
        """Handle x402 payment."""
        amount = float(payment_data["amount"])
        recipient = payment_data["recipient"]
        memo = payment_data.get("memo", "")
        
        # Send USDC payment
        try:
            tx_signature = await self.wallet.send_usdc(
                recipient=recipient,
                amount=amount,
                memo=memo,
            )
            return tx_signature
        except Exception as e:
            raise PaymentFailed(f"Payment failed: {e}")
    
    async def close(self):
        """Close the client."""
        await self._client.aclose()
        await self.wallet.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


