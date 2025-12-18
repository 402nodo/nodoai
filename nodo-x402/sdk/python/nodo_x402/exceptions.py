"""
NODO x402 SDK Exceptions
"""


class NodoError(Exception):
    """Base exception for NODO SDK."""
    pass


class PaymentRequired(NodoError):
    """Raised when payment is required (402)."""
    
    def __init__(self, amount: float, recipient: str, memo: str):
        self.amount = amount
        self.recipient = recipient
        self.memo = memo
        super().__init__(
            f"Payment of ${amount} USDC required. "
            f"Send to {recipient} with memo '{memo}'"
        )


class PaymentFailed(NodoError):
    """Raised when payment transaction fails."""
    pass


class APIError(NodoError):
    """Raised for API errors."""
    
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class WalletError(NodoError):
    """Raised for wallet-related errors."""
    pass


class InsufficientFunds(WalletError):
    """Raised when wallet has insufficient USDC."""
    
    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient USDC: need ${required}, have ${available}"
        )


