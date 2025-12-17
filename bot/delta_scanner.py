"""
Delta Neutral Scanner
Finds logical inconsistencies in related prediction markets.

Example:
- "BTC reach $150K" YES = $0.20
- "BTC reach $100K" YES = $0.15  <- ERROR! If BTC hits 150K, it MUST hit 100K first
- So 150K YES should NEVER be more expensive than 100K YES

Strategy: Buy the underpriced, sell the overpriced (or just buy the obvious winner)
"""
import re
import json
import random
from typing import Optional, List, Tuple
from dataclasses import dataclass
import httpx

GAMMA_URL = "https://gamma-api.polymarket.com"


@dataclass
class DeltaOpportunity:
    """A logical mispricing opportunity."""
    event_a: dict  # The "bigger" event (e.g., BTC 150K)
    event_b: dict  # The "smaller" event (e.g., BTC 100K)
    topic: str  # What they're about (BTC, ETH, etc)
    logic_error: str  # Description of the error
    profit_potential: float  # Estimated profit %
    confidence: int  # How sure we are about the logic (1-100)
    action: str  # What to do
    explanation: str = ""  # Detailed explanation of the logic


class DeltaScanner:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def scan(self, limit: int = 500) -> List[DeltaOpportunity]:
        """Scan for delta neutral opportunities."""
        
        # Fetch markets
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
        
        # Sort by profit potential
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
            
            # Extract threshold if present
            threshold = self._extract_threshold(question)
            topic = self._extract_topic(question)
            direction = self._extract_direction(question)
            
            return {
                "id": str(market.get("id", "")),
                "question": question,
                "yes_price": prices[0],
                "no_price": prices[1],
                "volume": volume,
                "url": f"https://polymarket.com/event/{slug}",
                "threshold": threshold,
                "topic": topic,
                "direction": direction,  # "above", "below", "reach", etc.
            }
        except:
            return None
    
    def _extract_threshold(self, question: str) -> Optional[float]:
        """Extract numeric threshold from question (price targets, not years)."""
        # Patterns like $100,000 or $100K or 100000
        patterns = [
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[kK]',  # $100K
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[mM]',  # $1M
            r'\$\s*([\d,]+(?:\.\d+)?)',          # $100,000
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, question)
            if match:
                num_str = match.group(1).replace(',', '')
                num = float(num_str)
                
                # Skip years (2020-2030 range)
                if 2020 <= num <= 2030:
                    continue
                
                # Skip very small numbers (likely not price targets)
                if num < 100:
                    continue
                
                if i == 0:  # K
                    num *= 1000
                elif i == 1:  # M
                    num *= 1_000_000
                
                return num
        
        return None
    
    def _extract_topic(self, question: str) -> str:
        """Extract the topic/subject of the question."""
        q_lower = question.lower()
        
        # Crypto
        if 'bitcoin' in q_lower or 'btc' in q_lower:
            return "BTC"
        elif 'ethereum' in q_lower or 'eth' in q_lower:
            return "ETH"
        elif 'solana' in q_lower or 'sol ' in q_lower:
            return "SOL"
        elif 'xrp' in q_lower or 'ripple' in q_lower:
            return "XRP"
        elif 'dogecoin' in q_lower or 'doge' in q_lower:
            return "DOGE"
        
        # Politics
        elif 'trump' in q_lower:
            return "TRUMP"
        elif 'biden' in q_lower:
            return "BIDEN"
        elif 'harris' in q_lower:
            return "HARRIS"
        elif 'musk' in q_lower or 'elon' in q_lower:
            return "MUSK"
        
        # Economy
        elif 'fed' in q_lower or 'interest rate' in q_lower or 'federal reserve' in q_lower:
            return "FED_RATE"
        elif 'inflation' in q_lower or 'cpi' in q_lower:
            return "INFLATION"
        elif 'gdp' in q_lower:
            return "GDP"
        
        # Stocks
        elif 'tesla' in q_lower or 'tsla' in q_lower:
            return "TESLA"
        elif 'sp500' in q_lower or 's&p' in q_lower or 'spy' in q_lower:
            return "SP500"
        elif 'nasdaq' in q_lower or 'qqq' in q_lower:
            return "NASDAQ"
        elif 'nvidia' in q_lower or 'nvda' in q_lower:
            return "NVIDIA"
        
        # Skip common words that aren't topics
        skip_words = {'will', 'the', 'be', 'is', 'are', 'have', 'has', 'do', 'does', 
                     'can', 'could', 'would', 'should', 'what', 'when', 'where', 'who',
                     'how', 'why', 'any', 'all', 'each', 'every', 'this', 'that'}
        
        # Try to extract meaningful capitalized word
        words = question.split()
        for w in words:
            clean = w.strip('?,."\'()[]')
            if clean and clean[0].isupper() and len(clean) > 2 and clean.lower() not in skip_words:
                return clean[:12]
        
        return "OTHER"
    
    def _extract_direction(self, question: str) -> str:
        """Extract the direction (above/below/reach)."""
        q_lower = question.lower()
        
        if 'above' in q_lower or 'over' in q_lower or 'exceed' in q_lower:
            return "above"
        elif 'below' in q_lower or 'under' in q_lower or 'drop' in q_lower or 'fall' in q_lower or 'dip' in q_lower:
            return "below"
        elif 'reach' in q_lower or 'hit' in q_lower:
            return "reach"
        else:
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
        """Find logical inconsistencies in a group of related markets."""
        opportunities = []
        
        # === 1. REACH thresholds (higher threshold should have lower YES price) ===
        reach_markets = [m for m in markets if m.get("threshold") and m.get("direction") in ["above", "reach"]]
        reach_markets.sort(key=lambda x: x["threshold"])
        
        for i in range(len(reach_markets) - 1):
            lower = reach_markets[i]  # e.g., BTC $100K
            higher = reach_markets[i + 1]  # e.g., BTC $150K
            
            if higher["threshold"] / lower["threshold"] < 1.1:
                continue
            
            # Strict error: higher YES > lower YES
            if higher["yes_price"] > lower["yes_price"] and lower["yes_price"] > 0.001:
                diff = higher["yes_price"] - lower["yes_price"]
                profit = (diff / max(lower["yes_price"], 0.01)) * 100
                
                explanation = (
                    f"ЛОГИКА: Если {topic} достигнет ${higher['threshold']:,.0f}, "
                    f"то он ОБЯЗАТЕЛЬНО пройдёт ${lower['threshold']:,.0f}.\n\n"
                    f"ОШИБКА: Рынок оценивает ${higher['threshold']:,.0f} ({higher['yes_price']:.0%}) "
                    f"ВЫШЕ чем ${lower['threshold']:,.0f} ({lower['yes_price']:.0%}).\n\n"
                    f"ВЫВОД: ${lower['threshold']:,.0f} YES недооценён - должен стоить минимум ${higher['yes_price']:.2f}"
                )
                
                opportunities.append(DeltaOpportunity(
                    event_a=higher, event_b=lower, topic=topic,
                    logic_error=f"${higher['threshold']:,.0f} YES ({higher['yes_price']:.2f}) > ${lower['threshold']:,.0f} YES ({lower['yes_price']:.2f})",
                    profit_potential=min(profit, 500),
                    confidence=90,
                    action=f"BUY '{lower['question'][:40]}' YES",
                    explanation=explanation
                ))
            
            # Near-miss: prices very close but should have bigger gap
            elif abs(higher["yes_price"] - lower["yes_price"]) < 0.02 and lower["yes_price"] > 0.05:
                explanation = (
                    f"ЛОГИКА: ${lower['threshold']:,.0f} легче достичь чем ${higher['threshold']:,.0f}.\n\n"
                    f"ПОДОЗРИТЕЛЬНО: Цены почти одинаковые ({lower['yes_price']:.2f} vs {higher['yes_price']:.2f}).\n\n"
                    f"ВЫВОД: Скоро рынок скорректируется - следи за расхождением"
                )
                
                opportunities.append(DeltaOpportunity(
                    event_a=higher, event_b=lower, topic=topic,
                    logic_error=f"${higher['threshold']:,.0f} ~ ${lower['threshold']:,.0f} - слишком близкие цены!",
                    profit_potential=5,
                    confidence=60,
                    action=f"Следи за расхождением",
                    explanation=explanation
                ))
        
        # === 2. DIP/BELOW thresholds (lower threshold should have lower YES price) ===
        dip_markets = [m for m in markets if m.get("threshold") and m.get("direction") == "below"]
        dip_markets.sort(key=lambda x: x["threshold"])
        
        for i in range(len(dip_markets) - 1):
            lower = dip_markets[i]  # e.g., BTC dip to $50K
            higher = dip_markets[i + 1]  # e.g., BTC dip to $70K
            
            # For dips: P(dip to $50K) <= P(dip to $70K)
            # So $50K YES should be <= $70K YES
            
            if lower["yes_price"] > higher["yes_price"] and higher["yes_price"] > 0.001:
                diff = lower["yes_price"] - higher["yes_price"]
                profit = (diff / max(higher["yes_price"], 0.01)) * 100
                
                explanation = (
                    f"ЛОГИКА: Если {topic} упадёт до ${lower['threshold']:,.0f}, "
                    f"он ОБЯЗАТЕЛЬНО упадёт до ${higher['threshold']:,.0f} (выше).\n\n"
                    f"ОШИБКА: Dip до ${lower['threshold']:,.0f} ({lower['yes_price']:.0%}) "
                    f"оценён ВЫШЕ чем dip до ${higher['threshold']:,.0f} ({higher['yes_price']:.0%}).\n\n"
                    f"ВЫВОД: Dip до ${higher['threshold']:,.0f} YES недооценён"
                )
                
                opportunities.append(DeltaOpportunity(
                    event_a=lower, event_b=higher, topic=topic,
                    logic_error=f"Dip ${lower['threshold']:,.0f} YES ({lower['yes_price']:.2f}) > Dip ${higher['threshold']:,.0f} YES ({higher['yes_price']:.2f})",
                    profit_potential=min(profit, 500),
                    confidence=85,
                    action=f"BUY 'Dip to ${higher['threshold']:,.0f}' YES",
                    explanation=explanation
                ))
        
        # === 3. Look for interesting spreads (good opportunities even if not errors) ===
        all_threshold = [m for m in markets if m.get("threshold")]
        for m in all_threshold:
            total = m["yes_price"] + m["no_price"]
            if total < 0.95 and m["volume"] > 5000:
                profit = ((1.0 - total) / total) * 100
                
                explanation = (
                    f"ЛОГИКА: YES + NO всегда должно = $1.00 (один из них точно сработает).\n\n"
                    f"ОШИБКА: YES (${m['yes_price']:.2f}) + NO (${m['no_price']:.2f}) = ${total:.2f}\n"
                    f"Это меньше $1.00 на ${1.0-total:.2f}!\n\n"
                    f"ВЫВОД: Купи ОБА исхода - гарантированный профит ${(1.0-total):.2f} на каждый $1"
                )
                
                opportunities.append(DeltaOpportunity(
                    event_a=m, event_b=m, topic=topic,
                    logic_error=f"YES+NO = {total:.2f} < 1.00 (арбитраж!)",
                    profit_potential=profit,
                    confidence=95,
                    action=f"BUY BOTH: YES (${m['yes_price']:.2f}) + NO (${m['no_price']:.2f})",
                    explanation=explanation
                ))
        
        return opportunities
    
    async def close(self):
        await self.client.aclose()


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        scanner = DeltaScanner()
        opps = await scanner.scan()
        
        print(f"Found {len(opps)} opportunities\n")
        
        for i, opp in enumerate(opps[:5], 1):
            print(f"{i}. [{opp.topic}] {opp.logic_error}")
            print(f"   Profit: {opp.profit_potential:.1f}%")
            print(f"   Action: {opp.action}")
            print(f"   URLs: {opp.event_a['url']}")
            print()
        
        await scanner.close()
    
    asyncio.run(test())

