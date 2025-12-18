/**
 * NODO x402 SDK Errors
 */

export class NodoError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NodoError';
  }
}

export class PaymentRequired extends NodoError {
  public readonly amount: number;
  public readonly recipient: string;
  public readonly memo: string;

  constructor(amount: number, recipient: string, memo: string) {
    super(
      `Payment of $${amount} USDC required. Send to ${recipient} with memo '${memo}'`
    );
    this.name = 'PaymentRequired';
    this.amount = amount;
    this.recipient = recipient;
    this.memo = memo;
  }
}

export class PaymentFailed extends NodoError {
  constructor(message: string) {
    super(message);
    this.name = 'PaymentFailed';
  }
}

export class APIError extends NodoError {
  public readonly statusCode: number;

  constructor(statusCode: number, message: string) {
    super(`API Error ${statusCode}: ${message}`);
    this.name = 'APIError';
    this.statusCode = statusCode;
  }
}

export class WalletError extends NodoError {
  constructor(message: string) {
    super(message);
    this.name = 'WalletError';
  }
}

export class InsufficientFunds extends WalletError {
  public readonly required: number;
  public readonly available: number;

  constructor(required: number, available: number) {
    super(`Insufficient USDC: need $${required}, have $${available}`);
    this.name = 'InsufficientFunds';
    this.required = required;
    this.available = available;
  }
}


