"""
Delta Neutral Strategy for Prediction Markets

Delta Neutral means creating positions where you don't care about the outcome.
You profit from market inefficiencies, not from predicting correctly.

STRATEGIES:

1. RELATED MARKETS (Subset Arbitrage)
   - Market A: "Trump wins 2024" = 55%
   - Market B: "Republican wins 2024" = 52%
   - Problem: Trump IS a Republican, so A ⊂ B
   - If Trump wins → Republican wins (always)
   - So P(Trump) should ALWAYS be <= P(Republican)
   - If P(Trump) > P(Republican) → ARBITRAGE!
   - Action: Short Trump, Long Republican

2. CALENDAR SPREAD (Time-based)
   - Market A: "BTC > $100K by March 2025" = 40%
   - Market B: "BTC > $100K by Dec 2025" = 65%
   - If March happens → December also happens
   - So P(March) <= P(December) always
   - Trade the spread when it's mispriced

3. COMPLEMENTARY MARKETS
   - Market A: "Fed cuts rates in 2025" = 70%
   - Market B: "Recession in 2025" = 30%
   - These are correlated but not deterministic
   - Can hedge one with the other

4. MULTI-OUTCOME REBALANCING
   - Market: "Who wins?" Trump 45%, Harris 40%, Other 10%
   - Keep balanced portfolio, profit from volatility
"""
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.table import Table

from config import config
from platforms import PlatformMarket, PolymarketPlatform


@dataclass
class RelatedMarketPair:
    """Two markets where one logically implies the other."""
    
    # The subset market (e.g., "Trump wins")
    subset_market: PlatformMarket
    subset_yes_price: float
    
    # The superset market (e.g., "Republican wins")  
    superset_market: PlatformMarket
    superset_yes_price: float
    
    # Relationship type
    relationship: str  # "subset", "calendar", "complementary"
    confidence: float  # How confident we are in the relationship
    
    @property
    def mispricing(self) -> float:
        """
        Calculate mispricing.
        If subset > superset, that's mispriced.
        Returns the spread (positive = opportunity)
        """
        return self.subset_yes_price - self.superset_yes_price
    
    @property
    def is_mispriced(self) -> bool:
        """Check if there's a mispricing opportunity."""
        # Subset should always be <= superset
        # Add small buffer for fees/noise
        return self.mispricing > 0.02  # 2% threshold
    
    @property
    def strategy(self) -> str:
        """Describe the delta neutral strategy."""
        if self.mispricing > 0:
            return f"SHORT '{self.subset_market.question[:30]}' + LONG '{self.superset_market.question[:30]}'"
        return "No action needed"
    
    def calculate_hedge(self, investment: float) -> dict:
        """
        Calculate hedge positions for delta neutral.
        
        Strategy when subset > superset:
        - Short subset (or buy NO on subset)
        - Long superset (buy YES on superset)
        
        Outcomes:
        1. Subset wins (Trump wins) → Both markets YES → net zero
        2. Superset wins but not subset (Other Republican) → Superset YES, Subset NO → PROFIT
        3. Neither wins → Both NO → net zero
        """
        if not self.is_mispriced:
            return {"error": "Not mispriced enough"}
        
        # Split investment between positions
        half = investment / 2
        
        # Position 1: Buy NO on subset (short subset)
        subset_no_price = 1 - self.subset_yes_price
        subset_no_shares = half / subset_no_price
        
        # Position 2: Buy YES on superset (long superset)
        superset_yes_shares = half / self.superset_yes_price
        
        # Calculate outcomes
        # Scenario 1: Subset wins (Trump wins → Republican wins)
        scenario1_pnl = (
            subset_no_shares * 0 +  # NO loses
            superset_yes_shares * 1 - investment  # YES wins
        )
        
        # Scenario 2: Superset wins, subset loses (Other Republican wins)
        scenario2_pnl = (
            subset_no_shares * 1 +  # NO wins  
            superset_yes_shares * 1 - investment  # YES wins
        )
        
        # Scenario 3: Neither wins (Democrat wins)
        scenario3_pnl = (
            subset_no_shares * 1 +  # NO wins
            superset_yes_shares * 0 - investment  # YES loses
        )
        
        return {
            "investment": investment,
            "subset_no_position": half,
            "subset_no_shares": subset_no_shares,
            "superset_yes_position": half,
            "superset_yes_shares": superset_yes_shares,
            "scenario_subset_wins": scenario1_pnl,
            "scenario_superset_only": scenario2_pnl,
            "scenario_neither": scenario3_pnl,
            "min_pnl": min(scenario1_pnl, scenario2_pnl, scenario3_pnl),
            "max_pnl": max(scenario1_pnl, scenario2_pnl, scenario3_pnl),
        }


@dataclass
class CalendarSpread:
    """Two markets for same event but different timeframes."""
    
    # Earlier deadline market
    early_market: PlatformMarket
    early_yes_price: float
    early_deadline: str
    
    # Later deadline market
    late_market: PlatformMarket
    late_yes_price: float
    late_deadline: str
    
    @property
    def spread(self) -> float:
        """Price difference (late - early)."""
        return self.late_yes_price - self.early_yes_price
    
    @property
    def is_mispriced(self) -> bool:
        """
        Early should always be <= late.
        If something happens by March, it definitely happened by December.
        """
        # If early > late, something is wrong
        return self.early_yes_price > self.late_yes_price + 0.02


# Common related market patterns to detect
RELATED_PATTERNS = [
    # Politics - Candidate ⊂ Party
    {
        "subset_keywords": ["trump", "donald"],
        "superset_keywords": ["republican", "gop"],
        "relationship": "candidate_party",
    },
    {
        "subset_keywords": ["harris", "kamala"],
        "superset_keywords": ["democrat", "democratic"],
        "relationship": "candidate_party",
    },
    {
        "subset_keywords": ["biden", "joe"],
        "superset_keywords": ["democrat", "democratic"],
        "relationship": "candidate_party",
    },
    
    # Crypto - Specific price ⊂ General price
    {
        "subset_keywords": ["150k", "150,000", "150000"],
        "superset_keywords": ["100k", "100,000", "100000"],
        "relationship": "price_threshold",
        "asset": "btc",
    },
    {
        "subset_keywords": ["200k", "200,000"],
        "superset_keywords": ["150k", "100k"],
        "relationship": "price_threshold",
        "asset": "btc",
    },
    
    # Time-based (calendar)
    {
        "subset_keywords": ["q1", "january", "february", "march"],
        "superset_keywords": ["2025", "q4", "december", "end of year"],
        "relationship": "calendar",
    },
]


class DeltaNeutralScanner:
    """
    Scans for delta neutral opportunities in prediction markets.
    """
    
    def __init__(self):
        self.console = Console()
        self.platform = PolymarketPlatform()
    
    def scan(self, limit: int = 100) -> tuple[list[RelatedMarketPair], list[CalendarSpread]]:
        """
        Scan for delta neutral opportunities.
        
        Returns:
            Tuple of (related_pairs, calendar_spreads)
        """
        logger.info("Scanning for Delta Neutral opportunities...")
        
        # Fetch markets
        markets = self.platform.get_markets(limit=limit)
        
        if not markets:
            logger.warning("No markets fetched")
            return [], []
        
        logger.info(f"Analyzing {len(markets)} markets...")
        
        # Find related pairs
        related_pairs = self._find_related_pairs(markets)
        
        # Find calendar spreads
        calendar_spreads = self._find_calendar_spreads(markets)
        
        # Filter to mispriced only
        mispriced_pairs = [p for p in related_pairs if p.is_mispriced]
        mispriced_calendars = [c for c in calendar_spreads if c.is_mispriced]
        
        logger.info(f"Found {len(mispriced_pairs)} mispriced related pairs")
        logger.info(f"Found {len(mispriced_calendars)} mispriced calendar spreads")
        
        return mispriced_pairs, mispriced_calendars
    
    def _find_related_pairs(self, markets: list[PlatformMarket]) -> list[RelatedMarketPair]:
        """Find pairs of markets with subset/superset relationship."""
        pairs = []
        
        for i, m1 in enumerate(markets):
            for m2 in markets[i+1:]:
                relationship = self._detect_relationship(m1, m2)
                if relationship:
                    # Determine which is subset
                    if relationship["subset"] == "m1":
                        subset, superset = m1, m2
                    else:
                        subset, superset = m2, m1
                    
                    pairs.append(RelatedMarketPair(
                        subset_market=subset,
                        subset_yes_price=subset.best_yes_price or 0,
                        superset_market=superset,
                        superset_yes_price=superset.best_yes_price or 0,
                        relationship=relationship["type"],
                        confidence=relationship["confidence"]
                    ))
        
        return pairs
    
    def _detect_relationship(self, m1: PlatformMarket, m2: PlatformMarket) -> Optional[dict]:
        """
        Detect if two markets have a logical relationship.
        Returns None if no relationship found.
        
        IMPORTANT: We need to check the DIRECTION of the price movement:
        - "reach $X" = price goes UP to X
        - "dip to $X" = price goes DOWN to X
        
        For REACH (upward):
        - "BTC reach $150K" implies "BTC reach $100K" (higher implies lower)
        - So $150K is SUBSET of $100K
        
        For DIP (downward):
        - "BTC dip to $50K" implies "BTC dip to $70K" (lower implies higher)
        - So $50K is SUBSET of $70K
        """
        q1 = m1.question.lower()
        q2 = m2.question.lower()
        
        # Check for candidate/party relationship
        # Trump winning implies Republican winning
        if self._has_keywords(q1, ["trump"]) and self._has_keywords(q2, ["republican"]):
            if self._same_event_context(q1, q2):  # Same election
                return {"type": "candidate_party", "subset": "m1", "confidence": 0.9}
        
        if self._has_keywords(q2, ["trump"]) and self._has_keywords(q1, ["republican"]):
            if self._same_event_context(q1, q2):
                return {"type": "candidate_party", "subset": "m2", "confidence": 0.9}
        
        # Harris/Democrat
        if self._has_keywords(q1, ["harris", "kamala"]) and self._has_keywords(q2, ["democrat"]):
            if self._same_event_context(q1, q2):
                return {"type": "candidate_party", "subset": "m1", "confidence": 0.9}
        
        if self._has_keywords(q2, ["harris", "kamala"]) and self._has_keywords(q1, ["democrat"]):
            if self._same_event_context(q1, q2):
                return {"type": "candidate_party", "subset": "m2", "confidence": 0.9}
        
        # BTC price thresholds - need to check direction!
        btc_info_1 = self._extract_btc_price_info(q1)
        btc_info_2 = self._extract_btc_price_info(q2)
        
        if btc_info_1 and btc_info_2:
            # Must be same direction (both "reach" or both "dip")
            if btc_info_1["direction"] != btc_info_2["direction"]:
                return None  # Not related
            
            direction = btc_info_1["direction"]
            price1 = btc_info_1["price"]
            price2 = btc_info_2["price"]
            
            if direction == "reach":
                # For REACH: higher price is subset (reaching $150K implies reached $100K)
                if price1 > price2:
                    return {"type": "btc_reach_threshold", "subset": "m1", "confidence": 0.95}
                elif price2 > price1:
                    return {"type": "btc_reach_threshold", "subset": "m2", "confidence": 0.95}
            
            elif direction == "dip":
                # For DIP: lower price is subset (dipping to $50K implies dipped to $70K)
                if price1 < price2:
                    return {"type": "btc_dip_threshold", "subset": "m1", "confidence": 0.95}
                elif price2 < price1:
                    return {"type": "btc_dip_threshold", "subset": "m2", "confidence": 0.95}
        
        return None
    
    def _has_keywords(self, text: str, keywords: list[str]) -> bool:
        """Check if text contains any of the keywords."""
        return any(kw in text for kw in keywords)
    
    def _same_event_context(self, q1: str, q2: str) -> bool:
        """Check if two questions are about the same event."""
        # Simple heuristic: share year and event type
        years = ["2024", "2025", "2026"]
        shared_year = any(y in q1 and y in q2 for y in years)
        
        events = ["election", "president", "win"]
        shared_event = any(e in q1 and e in q2 for e in events)
        
        return shared_year and shared_event
    
    def _extract_btc_threshold(self, text: str) -> Optional[float]:
        """Extract BTC price threshold from question (legacy)."""
        info = self._extract_btc_price_info(text)
        return info["price"] if info else None
    
    def _extract_btc_price_info(self, text: str) -> Optional[dict]:
        """
        Extract BTC price info including direction.
        
        Returns:
            {"price": float, "direction": "reach"|"dip"} or None
        """
        import re
        
        text = text.lower()
        
        if "btc" not in text and "bitcoin" not in text:
            return None
        
        # Determine direction
        direction = None
        if any(w in text for w in ["reach", "hit", "above", "over", "exceed"]):
            direction = "reach"
        elif any(w in text for w in ["dip", "fall", "below", "drop", "under"]):
            direction = "dip"
        else:
            return None  # Unknown direction
        
        # Extract price - match patterns like "$100,000", "100k", "100000"
        price = None
        
        # Pattern: $100,000 or $100000
        match = re.search(r'\$?([\d,]+)', text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                price = float(price_str)
            except:
                pass
        
        # Pattern: 100k or 100K
        if not price:
            match = re.search(r'(\d+)k\b', text, re.IGNORECASE)
            if match:
                price = float(match.group(1)) * 1000
        
        if price and price > 1000:  # Sanity check - BTC price should be > $1000
            return {"price": price, "direction": direction}
        
        return None
    
    def _find_calendar_spreads(self, markets: list[PlatformMarket]) -> list[CalendarSpread]:
        """Find calendar spread opportunities."""
        # Group markets by similar questions but different timeframes
        # This is complex - would need NLP to properly match
        # Simplified: look for same keywords with different dates
        
        # TODO: Implement proper calendar spread detection
        return []
    
    def display_related_pairs(self, pairs: list[RelatedMarketPair]):
        """Display related market pairs."""
        if not pairs:
            self.console.print("[yellow]No mispriced related market pairs found.[/yellow]")
            return
        
        table = Table(title="Delta Neutral: Related Market Pairs")
        table.add_column("Subset Market", style="cyan", max_width=35)
        table.add_column("YES Price", justify="right")
        table.add_column("Superset Market", style="green", max_width=35)
        table.add_column("YES Price", justify="right")
        table.add_column("Mispricing", justify="right", style="bold yellow")
        
        for pair in pairs:
            mispricing_str = f"{pair.mispricing*100:.2f}%"
            if pair.is_mispriced:
                mispricing_str = f"[bold red]{mispricing_str}[/bold red]"
            
            table.add_row(
                pair.subset_market.question[:35],
                f"${pair.subset_yes_price:.3f}",
                pair.superset_market.question[:35],
                f"${pair.superset_yes_price:.3f}",
                mispricing_str
            )
        
        self.console.print(table)
    
    def display_opportunity_details(self, pair: RelatedMarketPair, investment: float = 100):
        """Display detailed delta neutral strategy."""
        self.console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
        self.console.print("[bold]DELTA NEUTRAL OPPORTUNITY[/bold]")
        self.console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
        
        self.console.print("[bold]Markets:[/bold]")
        self.console.print(f"  SUBSET:   {pair.subset_market.question}")
        self.console.print(f"            YES = ${pair.subset_yes_price:.3f}")
        self.console.print(f"  SUPERSET: {pair.superset_market.question}")
        self.console.print(f"            YES = ${pair.superset_yes_price:.3f}")
        
        self.console.print(f"\n[bold]Relationship:[/bold] {pair.relationship}")
        self.console.print(f"[bold]Mispricing:[/bold] {pair.mispricing*100:.2f}%")
        
        self.console.print(f"\n[bold]Why This Is Wrong:[/bold]")
        self.console.print(f"  If '{pair.subset_market.question[:40]}...' is YES,")
        self.console.print(f"  then '{pair.superset_market.question[:40]}...' MUST also be YES.")
        self.console.print(f"  So P(subset) should be <= P(superset)")
        self.console.print(f"  But we have: {pair.subset_yes_price:.1%} > {pair.superset_yes_price:.1%}")
        
        self.console.print(f"\n[bold]Strategy:[/bold]")
        self.console.print(f"  1. BUY NO on subset (short it) @ ${1-pair.subset_yes_price:.3f}")
        self.console.print(f"  2. BUY YES on superset (long it) @ ${pair.superset_yes_price:.3f}")
        
        hedge = pair.calculate_hedge(investment)
        
        if "error" not in hedge:
            self.console.print(f"\n[bold]With ${investment} Investment:[/bold]")
            self.console.print(f"  Position 1 (NO subset):  ${hedge['subset_no_position']:.2f} ({hedge['subset_no_shares']:.2f} shares)")
            self.console.print(f"  Position 2 (YES superset): ${hedge['superset_yes_position']:.2f} ({hedge['superset_yes_shares']:.2f} shares)")
            
            self.console.print(f"\n[bold]Outcome Scenarios:[/bold]")
            self.console.print(f"  Scenario 1 (Subset wins):     ${hedge['scenario_subset_wins']:+.2f}")
            self.console.print(f"  Scenario 2 (Superset only):   ${hedge['scenario_superset_only']:+.2f}")
            self.console.print(f"  Scenario 3 (Neither wins):    ${hedge['scenario_neither']:+.2f}")
            
            self.console.print(f"\n[bold]Risk Profile:[/bold]")
            self.console.print(f"  Worst case:  ${hedge['min_pnl']:+.2f}")
            self.console.print(f"  Best case:   ${hedge['max_pnl']:+.2f}")


# Singleton
delta_scanner = DeltaNeutralScanner()


if __name__ == "__main__":
    import sys
    import os
    
    # Fix Windows console
    if sys.platform == "win32":
        os.system("chcp 65001 >nul 2>&1")
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    console = Console()
    console.print("[bold cyan]Delta Neutral Scanner[/bold cyan]\n")
    
    scanner = DeltaNeutralScanner()
    related_pairs, calendar_spreads = scanner.scan(limit=100)
    
    # Show all pairs (not just mispriced) for demo
    console.print("\n[bold]All Related Market Pairs Found:[/bold]")
    
    all_pairs = scanner._find_related_pairs(scanner.platform.get_markets(limit=100))
    
    if all_pairs:
        scanner.display_related_pairs(all_pairs)
        
        # Show details of best opportunity
        mispriced = [p for p in all_pairs if p.is_mispriced]
        if mispriced:
            console.print("\n[bold green]MISPRICED OPPORTUNITY FOUND![/bold green]")
            scanner.display_opportunity_details(mispriced[0])
    else:
        console.print("[yellow]No related market pairs detected.[/yellow]")
        console.print("[dim]This could mean:")
        console.print("  - Markets are efficiently priced")
        console.print("  - Need more markets to analyze")
        console.print("  - Need better relationship detection[/dim]")

