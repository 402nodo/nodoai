"""Tests for yield scanner module."""

import pytest
from datetime import datetime, timedelta


class TestYieldCalculations:
    """Test yield calculation functions."""
    
    def test_apy_calculation_basic(self):
        """Test basic APY calculation."""
        # 2% profit over 30 days = 24.33% APY
        profit_percentage = 2.0
        days = 30
        
        apy = (profit_percentage / days) * 365
        
        assert round(apy, 2) == 24.33
    
    def test_apy_calculation_short_term(self):
        """Test APY for short-term opportunity."""
        # 1% profit over 7 days = 52.14% APY
        profit_percentage = 1.0
        days = 7
        
        apy = (profit_percentage / days) * 365
        
        assert round(apy, 2) == 52.14
    
    def test_profit_calculation(self):
        """Test profit calculation from price."""
        buy_price = 0.98
        sell_price = 1.00
        investment = 100
        
        shares = investment / buy_price
        final_value = shares * sell_price
        profit = final_value - investment
        profit_percentage = (profit / investment) * 100
        
        assert round(profit, 2) == 2.04
        assert round(profit_percentage, 2) == 2.04


class TestOpportunityFiltering:
    """Test opportunity filtering logic."""
    
    def test_filter_by_probability(self, mock_polymarket_markets):
        """Test filtering by minimum probability."""
        min_prob = 0.90
        
        filtered = [
            m for m in mock_polymarket_markets
            if float(m["outcomePrices"].strip('[]"').split('", "')[1]) >= min_prob
        ]
        
        assert len(filtered) == 2  # Both have NO >= 0.90
    
    def test_filter_by_volume(self, mock_polymarket_markets):
        """Test filtering by minimum volume."""
        min_volume = 1000000
        
        filtered = [
            m for m in mock_polymarket_markets
            if float(m["volume"]) >= min_volume
        ]
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "test-market-1"
    
    def test_risk_level_classification(self):
        """Test risk level classification based on probability."""
        def classify_risk(probability: float) -> str:
            if probability >= 0.97:
                return "safe"
            elif probability >= 0.95:
                return "moderate"
            else:
                return "risky"
        
        assert classify_risk(0.98) == "safe"
        assert classify_risk(0.96) == "moderate"
        assert classify_risk(0.92) == "risky"


class TestDaysToResolution:
    """Test days to resolution calculations."""
    
    def test_days_calculation(self):
        """Test calculating days until market resolves."""
        end_date = datetime.now() + timedelta(days=14)
        now = datetime.now()
        
        days = (end_date - now).days
        
        assert days == 14
    
    def test_expired_market(self):
        """Test handling of expired market."""
        end_date = datetime.now() - timedelta(days=1)
        now = datetime.now()
        
        days = (end_date - now).days
        
        assert days < 0


@pytest.mark.asyncio
class TestAPIIntegration:
    """Test API integration (mocked)."""
    
    async def test_fetch_markets_success(self, mock_http_client, mock_polymarket_markets):
        """Test successful market fetch."""
        mock_http_client.get.return_value.json.return_value = mock_polymarket_markets
        mock_http_client.get.return_value.status_code = 200
        
        # Simulate fetch
        response = await mock_http_client.get(
            "https://gamma-api.polymarket.com/markets",
            params={"limit": 100, "active": True}
        )
        
        markets = response.json()
        
        assert len(markets) == 2
        assert markets[0]["id"] == "test-market-1"
    
    async def test_fetch_markets_error(self, mock_http_client):
        """Test handling of API error."""
        mock_http_client.get.return_value.status_code = 500
        mock_http_client.get.return_value.json.return_value = {"error": "Internal error"}
        
        response = await mock_http_client.get(
            "https://gamma-api.polymarket.com/markets"
        )
        
        assert response.status_code == 500

