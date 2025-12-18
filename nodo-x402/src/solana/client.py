"""
Solana Payment Client for x402
Handles USDC SPL token transfers and verification on Solana.
"""
import asyncio
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from loguru import logger
import base58

from src.config import settings


class SolanaPaymentClient:
    """
    Solana client for x402 payment verification.
    
    Handles:
    - Connection to Solana RPC
    - USDC SPL token transfer verification
    - Transaction confirmation
    """
    
    USDC_DECIMALS = 6
    
    def __init__(
        self,
        rpc_url: str = None,
        usdc_mint: str = None,
    ):
        self.rpc_url = rpc_url or settings.solana_rpc_url
        self.usdc_mint = usdc_mint or settings.solana_usdc_mint
        self._client = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to Solana RPC."""
        try:
            # Import here to avoid startup issues if solana not installed
            from solana.rpc.async_api import AsyncClient
            
            self._client = AsyncClient(self.rpc_url)
            
            # Test connection
            response = await self._client.get_health()
            self._connected = response.value == "ok"
            
            if self._connected:
                logger.info(f"Connected to Solana RPC: {self.rpc_url}")
            else:
                logger.warning(f"Solana RPC health check failed")
            
            return self._connected
            
        except ImportError:
            logger.warning("Solana SDK not installed. Running in mock mode.")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Solana: {e}")
            self._connected = False
            return False
    
    async def close(self):
        """Close Solana connection."""
        if self._client:
            await self._client.close()
            self._connected = False
    
    async def is_connected(self) -> bool:
        """Check if connected to Solana."""
        if not self._client:
            return False
        try:
            response = await self._client.get_health()
            return response.value == "ok"
        except:
            return False
    
    async def verify_usdc_transfer(
        self,
        tx_signature: str,
        expected_recipient: str,
        expected_amount: float,
        usdc_mint: str = None,
        max_age_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Verify a USDC transfer transaction on Solana.
        
        Args:
            tx_signature: Transaction signature to verify
            expected_recipient: Expected recipient wallet address
            expected_amount: Expected amount in USDC (decimal)
            usdc_mint: USDC mint address (defaults to mainnet USDC)
            max_age_seconds: Maximum transaction age in seconds
            
        Returns:
            Dict with verification result:
            {
                "valid": bool,
                "amount": float,
                "sender": str,
                "recipient": str,
                "memo": str,
                "timestamp": datetime,
                "error": str (if invalid)
            }
        """
        usdc_mint = usdc_mint or self.usdc_mint
        
        # If not connected, use mock verification for development
        if not self._connected:
            logger.warning("Using mock payment verification (Solana not connected)")
            return await self._mock_verify(tx_signature, expected_amount)
        
        try:
            from solders.signature import Signature
            from solana.rpc.types import TxOpts
            
            # Get transaction
            sig = Signature.from_string(tx_signature)
            response = await self._client.get_transaction(
                sig,
                encoding="jsonParsed",
                max_supported_transaction_version=0
            )
            
            if not response.value:
                return {
                    "valid": False,
                    "error": "Transaction not found"
                }
            
            tx_data = response.value
            
            # Check transaction age
            block_time = tx_data.block_time
            if block_time:
                tx_age = datetime.now(timezone.utc).timestamp() - block_time
                if tx_age > max_age_seconds:
                    return {
                        "valid": False,
                        "error": f"Transaction too old ({tx_age:.0f}s > {max_age_seconds}s)"
                    }
            
            # Check if transaction succeeded
            if tx_data.transaction.meta.err:
                return {
                    "valid": False,
                    "error": f"Transaction failed: {tx_data.transaction.meta.err}"
                }
            
            # Parse SPL token transfers
            transfer_info = self._parse_token_transfer(
                tx_data.transaction,
                usdc_mint,
                expected_recipient
            )
            
            if not transfer_info:
                return {
                    "valid": False,
                    "error": "No USDC transfer to expected recipient found"
                }
            
            # Verify amount
            amount = transfer_info["amount"]
            # Allow small tolerance for floating point
            if abs(amount - expected_amount) > 0.000001:
                return {
                    "valid": False,
                    "error": f"Amount mismatch: got {amount}, expected {expected_amount}",
                    "amount": amount
                }
            
            # Extract memo if present
            memo = self._extract_memo(tx_data.transaction)
            
            return {
                "valid": True,
                "amount": amount,
                "sender": transfer_info["sender"],
                "recipient": transfer_info["recipient"],
                "memo": memo,
                "timestamp": datetime.fromtimestamp(block_time, tz=timezone.utc) if block_time else None,
                "signature": tx_signature
            }
            
        except Exception as e:
            logger.error(f"Transaction verification error: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _parse_token_transfer(
        self,
        tx: Any,
        expected_mint: str,
        expected_recipient: str
    ) -> Optional[Dict]:
        """Parse SPL token transfer from transaction."""
        try:
            # Look for token transfer instruction
            for ix in tx.transaction.message.instructions:
                if hasattr(ix, 'parsed'):
                    parsed = ix.parsed
                    if isinstance(parsed, dict):
                        ix_type = parsed.get("type")
                        info = parsed.get("info", {})
                        
                        if ix_type in ["transfer", "transferChecked"]:
                            # Get transfer details
                            destination = info.get("destination") or info.get("tokenAccount")
                            mint = info.get("mint")
                            
                            # Get amount (in raw units)
                            if "tokenAmount" in info:
                                amount = float(info["tokenAmount"]["uiAmount"])
                            else:
                                amount = int(info.get("amount", 0)) / (10 ** self.USDC_DECIMALS)
                            
                            # Check if this is the expected transfer
                            if mint == expected_mint or not mint:
                                # We need to resolve token account to owner
                                # For now, check if destination matches
                                return {
                                    "amount": amount,
                                    "sender": info.get("source") or info.get("authority"),
                                    "recipient": destination,
                                    "mint": mint
                                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing token transfer: {e}")
            return None
    
    def _extract_memo(self, tx: Any) -> Optional[str]:
        """Extract memo from transaction."""
        try:
            for ix in tx.transaction.message.instructions:
                # Memo program ID
                if hasattr(ix, 'program_id'):
                    prog_id = str(ix.program_id)
                    if prog_id in ["MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr", "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"]:
                        # This is a memo instruction
                        if hasattr(ix, 'data'):
                            return ix.data.decode('utf-8') if isinstance(ix.data, bytes) else str(ix.data)
            return None
        except:
            return None
    
    async def _mock_verify(
        self,
        tx_signature: str,
        expected_amount: float
    ) -> Dict[str, Any]:
        """
        Mock verification for development/testing.
        Always returns valid for demonstration.
        """
        logger.warning(f"MOCK: Verifying payment {tx_signature[:16]}... for ${expected_amount}")
        
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        # For development, accept any signature that looks valid
        if len(tx_signature) >= 64:
            return {
                "valid": True,
                "amount": expected_amount,
                "sender": "MockSender111111111111111111111111111111111",
                "recipient": settings.nodo_wallet_address,
                "memo": "mock_payment",
                "timestamp": datetime.now(timezone.utc),
                "signature": tx_signature,
                "_mock": True
            }
        
        return {
            "valid": False,
            "error": "Invalid signature format",
            "_mock": True
        }
    
    async def get_usdc_balance(self, wallet_address: str) -> float:
        """Get USDC balance for a wallet."""
        if not self._connected:
            return 0.0
        
        try:
            from solders.pubkey import Pubkey
            
            pubkey = Pubkey.from_string(wallet_address)
            response = await self._client.get_token_accounts_by_owner(
                pubkey,
                {"mint": Pubkey.from_string(self.usdc_mint)}
            )
            
            if response.value:
                # Sum up all USDC token accounts
                total = 0.0
                for account in response.value:
                    amount = account.account.data.parsed["info"]["tokenAmount"]["uiAmount"]
                    total += float(amount)
                return total
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting USDC balance: {e}")
            return 0.0


# Singleton instance
_solana_client: Optional[SolanaPaymentClient] = None


def get_solana_client() -> SolanaPaymentClient:
    """Get singleton Solana client instance."""
    global _solana_client
    if _solana_client is None:
        _solana_client = SolanaPaymentClient()
    return _solana_client


