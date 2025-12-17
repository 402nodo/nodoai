"""
Event Matcher - Match same events across different platforms.

Uses keyword-based matching with verification warnings.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from platforms.base import PlatformMarket, MarketCategory


@dataclass
class MatchedEvent:
    """Represents the same event found across multiple platforms."""
    event_id: str
    name: str
    category: MarketCategory
    
    markets: dict[str, PlatformMarket] = field(default_factory=dict)
    confidence: float = 0.0
    keywords: set[str] = field(default_factory=set)
    match_reason: str = ""
    needs_verification: bool = True  # Flag to warn user
    
    @property
    def platforms(self) -> list[str]:
        return list(self.markets.keys())
    
    @property
    def num_platforms(self) -> int:
        return len(self.markets)
    
    def get_prices(self, outcome: str = "Yes") -> dict[str, float]:
        prices = {}
        for platform, market in self.markets.items():
            price = market.get_outcome_price(outcome)
            if price is not None:
                prices[platform] = price
        return prices
    
    def get_best_buy(self, outcome: str = "Yes") -> tuple[str, float]:
        prices = self.get_prices(outcome)
        if not prices:
            return ("", 0.0)
        return min(prices.items(), key=lambda x: x[1])
    
    def get_best_sell(self, outcome: str = "Yes") -> tuple[str, float]:
        prices = self.get_prices(outcome)
        if not prices:
            return ("", 0.0)
        return max(prices.items(), key=lambda x: x[1])
    
    def price_spread(self, outcome: str = "Yes") -> float:
        prices = list(self.get_prices(outcome).values())
        if len(prices) < 2:
            return 0.0
        return max(prices) - min(prices)


class EventMatcher:
    """Matches same events across different platforms using keywords."""
    
    # Important named entities
    ENTITIES = {
        # People
        'trump', 'biden', 'harris', 'vance', 'newsom', 'desantis', 'musk', 'elon',
        'starmer', 'keir', 'putin', 'zelensky', 'xi', 'macron', 'scholz', 'modi',
        'khamenei', 'netanyahu', 'trudeau', 'milei', 'altman', 'zuckerberg',
        
        # Organizations
        'nato', 'fed', 'sec', 'congress', 'senate', 'supreme', 'court',
        'spacex', 'tesla', 'openai', 'twitter', 'meta', 'google',
        
        # Countries/Regions  
        'ukraine', 'russia', 'china', 'iran', 'israel', 'gaza', 'greenland',
        'taiwan', 'uk', 'britain', 'us', 'usa', 'america',
        
        # Topics
        'recession', 'ceasefire', 'war', 'pandemic', 'bitcoin', 'btc', 'crypto',
        'election', 'president', 'impeach', 'veto'
    }
    
    YEARS = {'2024', '2025', '2026', '2027', '2028'}
    
    def __init__(self, similarity_threshold: float = 0.45):
        self.similarity_threshold = similarity_threshold
    
    def match_markets(self, markets: list[PlatformMarket]) -> list[MatchedEvent]:
        """Group markets from different platforms into matched events."""
        if not markets:
            return []
        
        matched_events = []
        used_markets = set()
        
        # Group by platform first
        by_platform = {}
        for m in markets:
            if m.platform not in by_platform:
                by_platform[m.platform] = []
            by_platform[m.platform].append(m)
        
        platforms = list(by_platform.keys())
        
        # For each market in first platform, try to find matches in others
        if not platforms:
            return []
            
        main_platform = platforms[0]
        other_platforms = platforms[1:]
        
        for market in by_platform[main_platform]:
            market_key = f"{market.platform}:{market.market_id}"
            if market_key in used_markets:
                continue
            
            keywords = self._extract_keywords(market.question)
            if not keywords:
                continue
            
            # Find best match from each other platform
            matches = []
            for other in other_platforms:
                best_match = None
                best_score = 0
                
                for candidate in by_platform.get(other, []):
                    cand_key = f"{candidate.platform}:{candidate.market_id}"
                    if cand_key in used_markets:
                        continue
                    
                    score, reason = self._calculate_similarity(market, candidate, keywords)
                    if score > best_score and score >= self.similarity_threshold:
                        best_score = score
                        best_match = (candidate, score, reason)
                
                if best_match:
                    matches.append(best_match)
            
            if matches:
                event = MatchedEvent(
                    event_id=self._generate_event_id(market),
                    name=market.question[:80],
                    category=market.category,
                    keywords=keywords,
                    needs_verification=True
                )
                
                event.markets[market.platform] = market
                used_markets.add(market_key)
                
                for matched_market, confidence, reason in matches:
                    mkey = f"{matched_market.platform}:{matched_market.market_id}"
                    if mkey not in used_markets:
                        event.markets[matched_market.platform] = matched_market
                        used_markets.add(mkey)
                        event.confidence = max(event.confidence, confidence)
                        event.match_reason = reason
                
                if event.num_platforms > 1:
                    matched_events.append(event)
            
            used_markets.add(market_key)
        
        logger.info(f"Matched {len(matched_events)} cross-platform events")
        return matched_events
    
    def _extract_keywords(self, text: str) -> set[str]:
        """Extract important keywords from text."""
        text_lower = text.lower()
        words = set(re.findall(r'\b[a-z0-9]+\b', text_lower))
        
        # Get matching entities
        entities = words & self.ENTITIES
        
        # Get years
        years = set(re.findall(r'\b(202[4-9])\b', text))
        
        # Important action words
        actions = words & {'win', 'lose', 'leave', 'remain', 'resign', 'ceasefire',
                          'recession', 'cut', 'raise', 'reach', 'hit', 'join'}
        
        return entities | years | actions
    
    def _calculate_similarity(
        self, m1: PlatformMarket, m2: PlatformMarket, kw1: set[str] = None
    ) -> tuple[float, str]:
        """Calculate similarity between two markets."""
        kw1 = kw1 or self._extract_keywords(m1.question)
        kw2 = self._extract_keywords(m2.question)
        
        if not kw1 or not kw2:
            return 0.0, ""
        
        common = kw1 & kw2
        if not common:
            return 0.0, ""
        
        # Calculate Jaccard similarity
        union = kw1 | kw2
        jaccard = len(common) / len(union)
        
        # Bonus for entity matches
        entities_common = common & self.ENTITIES
        entity_bonus = 0.2 if entities_common else 0
        
        # Bonus for year match
        years_common = common & self.YEARS
        year_bonus = 0.15 if years_common else 0
        
        score = jaccard + entity_bonus + year_bonus
        reason = f"Common: {', '.join(sorted(common)[:5])}"
        
        return min(score, 1.0), reason
    
    def _generate_event_id(self, market: PlatformMarket) -> str:
        import hashlib
        kw = sorted(self._extract_keywords(market.question))
        return hashlib.md5(":".join(kw[:5]).encode()).hexdigest()[:12]


# Singleton
matcher = EventMatcher()
