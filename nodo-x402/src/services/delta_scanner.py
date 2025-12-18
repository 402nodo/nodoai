"""
Delta Scanner Service
Finds logical mispricing in related markets.

Copied and adapted from bot/delta_scanner.py
"""
import re
import json
import random
from typing import Optional, List
from dataclasses import dataclass

import httpx

GAMMA_URL = "https://gamma-api.polymarket.com"


@dataclass
class DeltaOpportunity:
    """A logical mispricing opportunity."""
    event_a: dict
    event_b: dict
    topic: str
    logic_error: str
    profit_potential: float
    confidence: int
    action: str
    explanation: str = ""


class DeltaScanner:
    """Scans for delta neutral / mispricing opportunities."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def scan(self, limit: int = 500) -> List[DeltaOpportunity]:
        """Scan for delta neutral opportunities."""
        try:
            offset = random.randint(0, 50)
            response = await self.client.get(
                f"{GAMMA_URL}/markets",
                params={"limit": limit, "active": "true", "closed": "false", "offset": offset}
            )
            response.raise_for_status()
            markets = response.json()
        except Exception as e:
            print(f"Scan error: {e}")
            return []
        
        # Parse markets
        parsed = []
        for m in markets:
            parsed_market = self._parse_market(m)
            if parsed_market:
                parsed.append(parsed_market)
        
        # Group by topic
        groups = self._group_by_topic(parsed)
        
        # Find inconsistencies
        opportunities = []
        for topic, markets_in_group in groups.items():
            opps = self._find_inconsistencies(topic, markets_in_group)
            opportunities.extend(opps)
        
        opportunities.sort(key=lambda x: x.profit_potential, reverse=True)
        return opportunities
    
    def _parse_market(self, market: dict) -> Optional[dict]:
        """Parse a market and extract relevant info."""
        try:
            question = market.get("question", "")
            if not question:
                return None
            
            outcomes_raw = market.get("outcomes", '["Yes", "No"]')
            prices_raw = market.get("outcomePrices", '["0.5", "0.5"]')
            
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            prices = [float(p) for p in (json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw)]
            
            if len(outcomes) != 2 or len(prices) != 2:
                return None
            
            volume = float(market.get("volume", 0))
            if volume < 1000:
                return None
            
            slug = market.get("slug", market.get("id", ""))
            
            return {
                "id": str(market.get("id", "")),
                "question": question,
                "yes_price": prices[0],
                "no_price": prices[1],
                "volume": volume,
                "url": f"https://polymarket.com/event/{slug}",
                "threshold": self._extract_threshold(question),
                "topic": self._extract_topic(question),
                "direction": self._extract_direction(question),
            }
        except:
            return None
    
    def _extract_threshold(self, question: str) -> Optional[float]:
        """Extract numeric threshold from question."""
        patterns = [
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[kK]',
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[mM]',
            r'\$\s*([\d,]+(?:\.\d+)?)',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, question)
            if match:
                num_str = match.group(1).replace(',', '')
                num = float(num_str)
                
                if 2020 <= num <= 2030:
                    continue
                if num < 100:
                    continue
                
                if i == 0:
                    num *= 1000
                elif i == 1:
                    num *= 1_000_000
                
                return num
        return None
    
    def _extract_topic(self, question: str) -> str:
        """Extract the topic of the question."""
        q_lower = question.lower()
        
        if 'bitcoin' in q_lower or 'btc' in q_lower:
            return "BTC"
        elif 'ethereum' in q_lower or 'eth' in q_lower:
            return "ETH"
        elif 'solana' in q_lower or 'sol ' in q_lower:
            return "SOL"
        elif 'trump' in q_lower:
            return "TRUMP"
        elif 'fed' in q_lower or 'interest rate' in q_lower:
            return "FED_RATE"
        
        return "OTHER"
    
    def _extract_direction(self, question: str) -> str:
        """Extract the direction."""
        q_lower = question.lower()
        
        if 'above' in q_lower or 'over' in q_lower:
            return "above"
        elif 'below' in q_lower or 'under' in q_lower or 'dip' in q_lower:
            return "below"
        elif 'reach' in q_lower or 'hit' in q_lower:
            return "reach"
        return "unknown"
    
    def _group_by_topic(self, markets: List[dict]) -> dict:
        """Group markets by topic."""
        groups = {}
        for m in markets:
            topic = m.get("topic", "OTHER")
            if topic not in groups:
                groups[topic] = []
            groups[topic].append(m)
        return groups
    
    def _find_inconsistencies(self, topic: str, markets: List[dict]) -> List[DeltaOpportunity]:
        """Find logical inconsistencies."""
        opportunities = []
        
        # REACH thresholds
        reach_markets = [m for m in markets if m.get("threshold") and m.get("direction") in ["above", "reach"]]
        reach_markets.sort(key=lambda x: x["threshold"])
        
        for i in range(len(reach_markets) - 1):
            lower = reach_markets[i]
            higher = reach_markets[i + 1]
            
            if higher["threshold"] / lower["threshold"] < 1.1:
                continue
            
            if higher["yes_price"] > lower["yes_price"] and lower["yes_price"] > 0.001:
                diff = higher["yes_price"] - lower["yes_price"]
                profit = (diff / max(lower["yes_price"], 0.01)) * 100
                
                explanation = (
                    f"LOGIC: If {topic} reaches ${higher['threshold']:,.0f}, "
                    f"it MUST pass ${lower['threshold']:,.0f}.\n\n"
                    f"ERROR: Market prices ${higher['threshold']:,.0f} ({higher['yes_price']:.0%}) "
                    f"HIGHER than ${lower['threshold']:,.0f} ({lower['yes_price']:.0%})."
                )
                
                opportunities.append(DeltaOpportunity(
                    event_a=higher, event_b=lower, topic=topic,
                    logic_error=f"${higher['threshold']:,.0f} YES ({higher['yes_price']:.2f}) > ${lower['threshold']:,.0f} YES ({lower['yes_price']:.2f})",
                    profit_potential=min(profit, 500),
                    confidence=90,
                    action=f"BUY '{lower['question'][:40]}' YES",
                    explanation=explanation
                ))
        
        # YES+NO < 1 arbitrage
        for m in markets:
            total = m["yes_price"] + m["no_price"]
            if total < 0.95 and m["volume"] > 5000:
                profit = ((1.0 - total) / total) * 100
                
                explanation = (
                    f"ARBITRAGE: YES + NO should always = $1.00.\n"
                    f"Current: YES (${m['yes_price']:.2f}) + NO (${m['no_price']:.2f}) = ${total:.2f}\n"
                    f"Free money: ${(1.0-total):.2f} per $1 invested"
                )
                
                opportunities.append(DeltaOpportunity(
                    event_a=m, event_b=m, topic=topic,
                    logic_error=f"YES+NO = {total:.2f} < 1.00",
                    profit_potential=profit,
                    confidence=95,
                    action=f"BUY BOTH",
                    explanation=explanation
                ))
        
        return opportunities
    
    async def close(self):
        await self.client.aclose()


