"""Pytest configuration and fixtures."""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_openrouter_response():
    """Mock response from OpenRouter API."""
    return {
        "id": "gen-123",
        "choices": [
            {
                "message": {
                    "content": '{"action": "BUY", "confidence": 85, "reasoning": "Test reasoning"}'
                }
            }
        ],
        "model": "anthropic/claude-3.5-sonnet",
        "usage": {"total_tokens": 100}
    }


@pytest.fixture
def mock_polymarket_markets():
    """Mock Polymarket markets data."""
    return [
        {
            "id": "test-market-1",
            "question": "Will BTC reach $150K by Dec 2025?",
            "outcomePrices": '["0.08", "0.92"]',
            "volume": "1250000",
            "endDate": "2025-12-31T00:00:00Z",
            "active": True
        },
        {
            "id": "test-market-2",
            "question": "Will ETH reach $10K by Dec 2025?",
            "outcomePrices": '["0.05", "0.95"]',
            "volume": "500000",
            "endDate": "2025-12-31T00:00:00Z",
            "active": True
        }
    ]


@pytest.fixture
def sample_opportunity():
    """Sample yield farming opportunity."""
    return {
        "market_id": "test-market-1",
        "question": "Will BTC reach $150K by Dec 2025?",
        "action": "BUY_NO",
        "price": 0.92,
        "potential_profit": 0.087,
        "apy": 45.2,
        "days_to_resolution": 14,
        "volume": 1250000,
        "risk_level": "safe"
    }


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for API calls."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client

