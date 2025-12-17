"""
Cross-Platform Arbitrage Scanner
Finds arbitrage opportunities across multiple prediction market platforms.

Strategy:
1. Fetch markets from all platforms
2. Match same events across platforms
3. Compare prices for arbitrage opportunities
4. Calculate profit considering fees
"""
from dataclasses import dataclass
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.table import Table

from config import config
from platforms import (
    PredictionPlatform,
    PlatformMarket,
    PolymarketPlatform,
    KalshiPlatform,
    AzuroPlatform,
    PredictItPlatform,
)
from event_matcher import EventMatcher, MatchedEvent


@dataclass
class CrossPlatformArbitrage:
    """
    Represents a cross-platform arbitrage opportunity.
    
    Strategy: Buy YES on one platform + Buy NO on another platform
    If total cost < $1, guaranteed profit regardless of outcome.
    """
    event: MatchedEvent
    
    # The arbitrage - buy OPPOSITE outcomes on different platforms
    yes_platform: str
    yes_price: float
    no_platform: str  
    no_price: float
    
    # Total cost and profits
    total_cost: float  # yes_price + no_price (should be < 1.0 for arb)
    gross_profit_pct: float
    net_profit_pct: float  # After fees
    
    # Fees
    yes_platform_fee: float
    no_platform_fee: float
    
    @property
    def is_profitable(self) -> bool:
        """Check if profitable after fees."""
        return self.net_profit_pct > config.MIN_PROFIT_THRESHOLD
    
    @property 
    def guaranteed_return(self) -> float:
        """One of the outcomes MUST pay $1."""
        return 1.0
    
    def calculate_returns(self, investment: float) -> dict:
        """
        Calculate returns for given investment.
        
        Strategy: Split investment proportionally between YES and NO
        to guarantee $1 payout per unit regardless of outcome.
        """
        # To guarantee $1 payout, we need to buy proportionally
        # If YES costs $0.40 and NO costs $0.55, total = $0.95
        # For every $0.95 invested, we get $1 back
        
        units = investment / self.total_cost  # How many "full sets" we can buy
        
        yes_investment = units * self.yes_price
        no_investment = units * self.no_price
        
        # Guaranteed return (one outcome will pay $1 per unit)
        gross_return = units * 1.0
        
        # Fees are paid on winnings
        # Whichever wins, we pay fee on that platform
        avg_fee = (self.yes_platform_fee + self.no_platform_fee) / 2
        fee_amount = gross_return * avg_fee
        
        net_return = gross_return - fee_amount
        net_profit = net_return - investment
        
        return {
            "investment": investment,
            "units": units,
            "yes_investment": yes_investment,
            "no_investment": no_investment,
            "yes_platform": self.yes_platform,
            "no_platform": self.no_platform,
            "gross_return": gross_return,
            "fee": fee_amount,
            "net_return": net_return,
            "net_profit": net_profit,
            "roi_pct": (net_profit / investment) * 100 if investment > 0 else 0
        }


class CrossPlatformScanner:
    """
    Scans multiple platforms for cross-platform arbitrage opportunities.
    """
    
    def __init__(self):
        self.console = Console()
        self.matcher = EventMatcher(similarity_threshold=0.5)
        
        # Initialize platforms
        self.platforms: dict[str, PredictionPlatform] = {}
        self._init_platforms()
    
    def _init_platforms(self):
        """Initialize all supported platforms."""
        try:
            self.platforms["polymarket"] = PolymarketPlatform()
            logger.info("Initialized Polymarket")
        except Exception as e:
            logger.warning(f"Failed to init Polymarket: {e}")
        
        try:
            self.platforms["kalshi"] = KalshiPlatform()
            logger.info("Initialized Kalshi")
        except Exception as e:
            logger.warning(f"Failed to init Kalshi: {e}")
        
        try:
            self.platforms["predictit"] = PredictItPlatform()
            logger.info("Initialized PredictIt")
        except Exception as e:
            logger.warning(f"Failed to init PredictIt: {e}")
        
        # Azuro is for sports, may not overlap much with others
        try:
            self.platforms["azuro"] = AzuroPlatform()
            logger.info("Initialized Azuro")
        except Exception as e:
            logger.warning(f"Failed to init Azuro: {e}")
    
    def scan(self, markets_per_platform: int = 50) -> list[CrossPlatformArbitrage]:
        """
        Scan all platforms for cross-platform arbitrage.
        
        Args:
            markets_per_platform: How many markets to fetch per platform
            
        Returns:
            List of arbitrage opportunities sorted by profit
        """
        logger.info(f"Starting cross-platform scan across {len(self.platforms)} platforms...")
        
        # 1. Fetch markets from all platforms
        all_markets = []
        for name, platform in self.platforms.items():
            try:
                markets = platform.get_markets(limit=markets_per_platform)
                all_markets.extend(markets)
                logger.info(f"  [{name}] {len(markets)} markets")
            except Exception as e:
                logger.error(f"  [{name}] Failed: {e}")
        
        if len(all_markets) < 2:
            logger.warning("Not enough markets to find cross-platform arbitrage")
            return []
        
        # 2. Match same events across platforms
        matched_events = self.matcher.match_markets(all_markets)
        multi_platform_events = [e for e in matched_events if e.num_platforms > 1]
        
        logger.info(f"Found {len(multi_platform_events)} events on multiple platforms")
        
        # 3. Find arbitrage opportunities
        opportunities = []
        for event in multi_platform_events:
            arbs = self._find_arbitrage(event)
            opportunities.extend(arbs)
        
        # Sort by profit
        opportunities.sort(key=lambda x: x.net_profit_pct, reverse=True)
        
        # Filter profitable only
        profitable = [o for o in opportunities if o.is_profitable]
        
        logger.info(f"Found {len(profitable)} profitable arbitrage opportunities")
        return profitable
    
    def _find_arbitrage(self, event: MatchedEvent) -> list[CrossPlatformArbitrage]:
        """
        Find cross-platform arbitrage opportunities.
        
        CORRECT STRATEGY:
        - Buy YES on platform with LOWEST YES price
        - Buy NO on platform with LOWEST NO price  
        - If total cost < $1.00, guaranteed profit!
        
        Example:
            Polymarket: YES=$0.55, NO=$0.47
            PredictIt:  YES=$0.50, NO=$0.52
            
            Best YES: PredictIt $0.50
            Best NO:  Polymarket $0.47
            Total:    $0.97 → 3% guaranteed profit!
        """
        opportunities = []
        
        # Only works for binary markets (YES/NO)
        # Collect YES and NO prices from each platform
        yes_prices = {}  # platform -> price
        no_prices = {}   # platform -> price
        
        for platform_name, market in event.markets.items():
            yes_price = market.best_yes_price
            no_price = market.best_no_price
            
            if yes_price and yes_price > 0:
                yes_prices[platform_name] = yes_price
            if no_price and no_price > 0:
                no_prices[platform_name] = no_price
        
        # Need prices from at least 2 platforms
        if len(yes_prices) < 1 or len(no_prices) < 1:
            return []
        
        # Find cheapest YES and cheapest NO (can be same or different platforms)
        best_yes = min(yes_prices.items(), key=lambda x: x[1])
        best_no = min(no_prices.items(), key=lambda x: x[1])
        
        # Calculate total cost
        total_cost = best_yes[1] + best_no[1]
        
        # Only arbitrage if total < 1.0 (guaranteed profit)
        if total_cost >= 1.0:
            return []
        
        # Must be different platforms for cross-platform arb
        if best_yes[0] == best_no[0]:
            # Same platform - this is intra-platform arb, skip
            return []
        
        # Get platform fees
        yes_platform = self.platforms.get(best_yes[0])
        no_platform = self.platforms.get(best_no[0])
        
        yes_fee = yes_platform.trading_fee if yes_platform else 0.02
        no_fee = no_platform.trading_fee if no_platform else 0.02
        
        # Calculate profit
        # Gross: spend $total_cost, get $1 back
        gross_profit = 1.0 - total_cost
        gross_profit_pct = (gross_profit / total_cost) * 100
        
        # Net: subtract fees (fee is on winnings, so on $1)
        avg_fee = (yes_fee + no_fee) / 2  # One will win, avg the fees
        net_profit = gross_profit - avg_fee
        net_profit_pct = (net_profit / total_cost) * 100
        
        opportunities.append(CrossPlatformArbitrage(
            event=event,
            yes_platform=best_yes[0],
            yes_price=best_yes[1],
            no_platform=best_no[0],
            no_price=best_no[1],
            total_cost=total_cost,
            gross_profit_pct=gross_profit_pct,
            net_profit_pct=net_profit_pct,
            yes_platform_fee=yes_fee,
            no_platform_fee=no_fee
        ))
        
        return opportunities
    
    def display_opportunities(self, opportunities: list[CrossPlatformArbitrage]):
        """Display opportunities in a table."""
        if not opportunities:
            self.console.print("[yellow]No cross-platform arbitrage opportunities found.[/yellow]")
            self.console.print("[dim]This means YES + NO prices across platforms >= $1.00[/dim]")
            return
        
        table = Table(title="Cross-Platform Arbitrage Opportunities")
        table.add_column("Event", style="cyan", max_width=30)
        table.add_column("Buy YES @", style="green")
        table.add_column("Buy NO @", style="blue")
        table.add_column("Total Cost", justify="right")
        table.add_column("Gross %", justify="right", style="green")
        table.add_column("Net %", justify="right", style="bold yellow")
        
        for opp in opportunities[:10]:  # Top 10
            table.add_row(
                opp.event.name[:30],
                f"{opp.yes_platform}\n${opp.yes_price:.3f}",
                f"{opp.no_platform}\n${opp.no_price:.3f}",
                f"${opp.total_cost:.3f}",
                f"{opp.gross_profit_pct:.2f}%",
                f"{opp.net_profit_pct:.2f}%"
            )
        
        self.console.print(table)
        self.console.print("\n[dim]Strategy: Buy YES on one platform + Buy NO on another.[/dim]")
        self.console.print("[dim]If total cost < $1.00, you profit regardless of outcome![/dim]")
    
    def display_opportunity_details(self, opp: CrossPlatformArbitrage, investment: float = 100):
        """Display detailed breakdown of opportunity."""
        returns = opp.calculate_returns(investment)
        
        self.console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        self.console.print(f"[bold]{opp.event.name}[/bold]")
        self.console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")
        
        # Price comparison across platforms
        self.console.print("[bold]Prices Across Platforms:[/bold]")
        for platform, market in opp.event.markets.items():
            yes_price = market.best_yes_price or 0
            no_price = market.best_no_price or 0
            total = yes_price + no_price
            
            yes_mark = " [green]<- BUY YES[/green]" if platform == opp.yes_platform else ""
            no_mark = " [blue]<- BUY NO[/blue]" if platform == opp.no_platform else ""
            
            self.console.print(f"  {platform}:")
            self.console.print(f"    YES: ${yes_price:.4f}{yes_mark}")
            self.console.print(f"    NO:  ${no_price:.4f}{no_mark}")
            self.console.print(f"    Sum: ${total:.4f}")
        
        # Strategy explanation
        self.console.print(f"\n[bold]Arbitrage Strategy:[/bold]")
        self.console.print(f"  1. Buy YES on [green]{opp.yes_platform}[/green] @ ${opp.yes_price:.4f}")
        self.console.print(f"  2. Buy NO on [blue]{opp.no_platform}[/blue] @ ${opp.no_price:.4f}")
        self.console.print(f"  [bold]Total cost: ${opp.total_cost:.4f}[/bold]")
        self.console.print(f"  [bold]Guaranteed payout: $1.00[/bold]")
        self.console.print(f"  [bold green]Guaranteed profit: ${1-opp.total_cost:.4f} ({opp.gross_profit_pct:.2f}%)[/bold green]")
        
        # Why it works
        self.console.print(f"\n[bold]Why This Works:[/bold]")
        self.console.print(f"  - If event happens: YES pays $1, NO pays $0")
        self.console.print(f"  - If event doesn't happen: YES pays $0, NO pays $1")
        self.console.print(f"  - Either way, you get $1 back!")
        
        # Returns with specific investment
        self.console.print(f"\n[bold]With ${investment:.0f} Investment:[/bold]")
        self.console.print(f"  Units purchased: {returns['units']:.2f}")
        self.console.print(f"  YES ({opp.yes_platform}): ${returns['yes_investment']:.2f}")
        self.console.print(f"  NO ({opp.no_platform}): ${returns['no_investment']:.2f}")
        self.console.print(f"  Guaranteed return: ${returns['gross_return']:.2f}")
        self.console.print(f"  Est. fees: -${returns['fee']:.2f}")
        self.console.print(f"  [bold green]Net profit: ${returns['net_profit']:.2f} ({returns['roi_pct']:.2f}%)[/bold green]")


# Singleton
cross_scanner = CrossPlatformScanner()


if __name__ == "__main__":
    import sys
    import os
    
    # Fix Windows console encoding
    if sys.platform == "win32":
        os.system("chcp 65001 >nul 2>&1")
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    from rich.console import Console
    console = Console()
    
    console.print("[bold cyan]Starting Cross-Platform Arbitrage Scanner...[/bold cyan]\n")
    
    scanner = CrossPlatformScanner()
    opportunities = scanner.scan(markets_per_platform=30)
    
    scanner.display_opportunities(opportunities)
    
    if opportunities:
        console.print("\n[bold]Best Opportunity Details:[/bold]")
        scanner.display_opportunity_details(opportunities[0])

