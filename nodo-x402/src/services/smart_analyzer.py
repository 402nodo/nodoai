"""
Smart Analyzer Service
Category-specific analysis for prediction events.

Copied and adapted from bot/smart_analyzer.py
"""
import re
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

import httpx


class EventCategory(Enum):
    CRYPTO_PRICE = "crypto_price"
    POLITICS = "politics"
    SPORTS = "sports"
    CELEBRITY = "celebrity"
    TECH = "tech"
    ECONOMY = "economy"
    OTHER = "other"


@dataclass
class EventAnalysis:
    """Analysis result."""
    category: EventCategory
    confidence_score: int
    predicted_outcome: str
    reasons: List[str]
    risks: List[str]
    verdict: str
    data_used: Dict


class SmartAnalyzer:
    """Smart event analyzer with category detection."""
    
    CRYPTO_KEYWORDS = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'solana', 'sol', 'price', 'reach']
    POLITICS_KEYWORDS = ['president', 'election', 'trump', 'biden', 'resign', 'impeach', 'vote']
    TECH_KEYWORDS = ['spacex', 'tesla', 'ai', 'launch', 'release', 'starship']
    ECONOMY_KEYWORDS = ['fed', 'rate', 'recession', 'inflation', 'gdp']
    
    def __init__(self):
        self.client = httpx.Client(timeout=10.0)
    
    def analyze(self, question: str, current_price: float, outcome: str, days_left: int) -> EventAnalysis:
        """Analyze an event."""
        q_lower = question.lower()
        category = self._categorize(q_lower)
        
        if category == EventCategory.CRYPTO_PRICE:
            return self._analyze_crypto(question, q_lower, current_price, outcome, days_left)
        elif category == EventCategory.POLITICS:
            return self._analyze_politics(question, q_lower, current_price, outcome, days_left)
        else:
            return self._analyze_generic(question, q_lower, current_price, outcome, days_left, category)
    
    def _categorize(self, q_lower: str) -> EventCategory:
        """Categorize the event."""
        scores = {
            EventCategory.CRYPTO_PRICE: sum(1 for kw in self.CRYPTO_KEYWORDS if kw in q_lower),
            EventCategory.POLITICS: sum(1 for kw in self.POLITICS_KEYWORDS if kw in q_lower),
            EventCategory.TECH: sum(1 for kw in self.TECH_KEYWORDS if kw in q_lower),
            EventCategory.ECONOMY: sum(1 for kw in self.ECONOMY_KEYWORDS if kw in q_lower),
        }
        
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else EventCategory.OTHER
    
    def _analyze_crypto(self, question: str, q_lower: str, price: float, outcome: str, days: int) -> EventAnalysis:
        """Analyze crypto events."""
        reasons = []
        risks = []
        data = {}
        
        # Extract target price
        target_price = self._extract_price(question)
        data['target_price'] = target_price
        
        # Get current crypto price
        crypto = "BTC"
        if 'ethereum' in q_lower or 'eth' in q_lower:
            crypto = "ETH"
        elif 'solana' in q_lower:
            crypto = "SOL"
        
        current_crypto_price = self._get_crypto_price(crypto)
        data['current_price'] = current_crypto_price
        data['crypto'] = crypto
        
        if target_price and current_crypto_price:
            if target_price > current_crypto_price:
                pct_needed = ((target_price - current_crypto_price) / current_crypto_price) * 100
                data['change_needed'] = f"+{pct_needed:.1f}%"
                
                if pct_needed > 100:
                    reasons.append(f"Needs {pct_needed:.0f}% growth (>2x)")
                    reasons.append(f"Current {crypto}: ${current_crypto_price:,.0f}")
                    reasons.append(f"In {days} days - highly unlikely")
                    verdict = f"NO very likely - {pct_needed:.0f}% growth unrealistic"
                elif pct_needed > 50:
                    reasons.append(f"Needs {pct_needed:.0f}% growth")
                    reasons.append("Only possible in strong bull run")
                    verdict = f"NO likely, but {pct_needed:.0f}% growth possible"
                else:
                    reasons.append(f"Only {pct_needed:.0f}% growth needed")
                    risks.append("Crypto volatility makes this achievable")
                    verdict = "Higher risk - growth is possible"
            else:
                reasons.append(f"Target ${target_price:,.0f} already reached!")
                verdict = "YES likely already triggered"
        else:
            reasons.append(f"Market prices at {price*100:.0f}%")
            verdict = "Limited data - trust market price"
        
        risks.append("Crypto markets are highly volatile")
        risks.append("News can rapidly change prices")
        
        return EventAnalysis(
            category=EventCategory.CRYPTO_PRICE,
            confidence_score=70 if target_price else 40,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used=data
        )
    
    def _analyze_politics(self, question: str, q_lower: str, price: float, outcome: str, days: int) -> EventAnalysis:
        """Analyze political events."""
        reasons = []
        risks = []
        
        if any(word in q_lower for word in ['resign', 'leave', 'step down']):
            reasons.append("Resignation events rarely happen quickly")
            reasons.append("Politicians typically hold onto power")
            if days < 30:
                reasons.append(f"Only {days} days - too short for such change")
            verdict = "NO likely - resignations are rare without clear cause"
        elif 'election' in q_lower:
            reasons.append("Election outcomes depend on many factors")
            risks.append("Polls often miss the actual result")
            verdict = "Depends on specific candidates and polls"
        else:
            reasons.append("Political events are often unpredictable")
            reasons.append(f"Market prices at {price*100:.0f}%")
            verdict = f"Check market price: {price*100:.0f}%"
        
        risks.append("Politics can shift rapidly")
        
        return EventAnalysis(
            category=EventCategory.POLITICS,
            confidence_score=60,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used={'category': 'politics', 'days_left': days}
        )
    
    def _analyze_generic(self, question: str, q_lower: str, price: float, outcome: str, days: int, category: EventCategory) -> EventAnalysis:
        """Generic analysis for other categories."""
        reasons = []
        risks = []
        
        if days <= 7:
            reasons.append(f"Only {days} days remaining")
            reasons.append("Short timeframe limits major changes")
        else:
            reasons.append(f"{days} days until resolution")
            risks.append("Longer timeframe = more uncertainty")
        
        if price >= 0.97:
            reasons.append(f"Market very confident: {price*100:.0f}%")
            verdict = f"{outcome} very likely ({price*100:.0f}%)"
        elif price >= 0.95:
            reasons.append(f"Market confident: {price*100:.0f}%")
            risks.append("5% chance of opposite outcome")
            verdict = f"{outcome} likely, but some risk"
        else:
            reasons.append(f"Moderate confidence: {price*100:.0f}%")
            risks.append("Significant chance of different outcome")
            verdict = "Higher risk!"
        
        return EventAnalysis(
            category=category,
            confidence_score=45,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used={'market_price': price, 'days': days}
        )
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price target from text."""
        patterns = [
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)',
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:m|M)',
            r'\$\s*([\d,]+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num_str = match.group(1).replace(',', '')
                num = float(num_str)
                
                full_match = match.group(0).lower()
                if 'k' in full_match:
                    num *= 1000
                elif 'm' in full_match:
                    num *= 1_000_000
                
                return num
        return None
    
    def _get_crypto_price(self, symbol: str) -> Optional[float]:
        """Get current crypto price."""
        try:
            ids = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana'}
            coin_id = ids.get(symbol, 'bitcoin')
            
            response = self.client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"}
            )
            data = response.json()
            return data[coin_id]['usd']
        except:
            fallbacks = {'BTC': 100000, 'ETH': 3500, 'SOL': 200}
            return fallbacks.get(symbol, 100000)
    
    def close(self):
        self.client.close()


