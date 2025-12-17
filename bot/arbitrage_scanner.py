"""
Intra-Platform Arbitrage Scanner
Finds arbitrage opportunities within Polymarket.

Types of arbitrage detected:
1. YES + NO < 100% - Buy both outcomes, guaranteed profit
2. Multi-outcome markets where sum of prices < 100%
"""
from dataclasses import dataclass
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.table import Table

from config import config
from polymarket_client import PolymarketClient, Market


@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity."""
    market: Market
    type: str  # "binary" or "multi_outcome"
    total_cost: float  # Cost to buy all outcomes (per $1 payout)
    gross_profit_pct: float  # Gross profit percentage
    net_profit_pct: float  # Net profit after fees
    optimal_allocation: dict[str, float]  # How much to allocate to each outcome
    
    @property
    def is_profitable(self) -> bool:
        """Check if opportunity is profitable after fees."""
        return self.net_profit_pct > config.MIN_PROFIT_THRESHOLD
    
    def calculate_returns(self, investment: float) -> dict:
        """
        Calculate expected returns for a given investment.
        
        Args:
            investment: Amount to invest in USDC
            
        Returns:
            Dict with investment breakdown and expected profit
        """
        # Amount bet on each outcome
        allocations = {}
        for outcome, ratio in self.optimal_allocation.items():
            allocations[outcome] = investment * ratio
        
        # Guaranteed return (one outcome will win)
        guaranteed_return = investment / self.total_cost
        
        # Gross profit
        gross_profit = guaranteed_return - investment
        
        # Net profit after fees
        fee = guaranteed_return * config.TRADING_FEE
        net_profit = gross_profit - fee
        
        return {
            "investment": investment,
            "allocations": allocations,
            "guaranteed_return": guaranteed_return,
            "gross_profit": gross_profit,
            "fee": fee,
            "net_profit": net_profit,
            "roi_pct": (net_profit / investment) * 100 if investment > 0 else 0
        }


class ArbitrageScanner:
    """
    Scans Polymarket for intra-platform arbitrage opportunities.
    """
    
    def __init__(self, client: Optional[PolymarketClient] = None):
        self.client = client or PolymarketClient()
        self.console = Console()
    
    def scan(self, limit: int = 100) -> list[ArbitrageOpportunity]:
        """
        Scan markets for arbitrage opportunities.
        
        Args:
            limit: Maximum number of markets to scan
            
        Returns:
            List of profitable arbitrage opportunities
        """
        logger.info(f"Scanning {limit} markets for arbitrage opportunities...")
        
        # Fetch active markets
        markets = self.client.get_markets(limit=limit, active=True)
        
        if not markets:
            logger.warning("No markets fetched")
            return []
        
        opportunities = []
        
        for market in markets:
            opp = self._analyze_market(market)
            if opp and opp.is_profitable:
                opportunities.append(opp)
                logger.success(
                    f"Found arbitrage: {market.question[:50]}... "
                    f"({opp.net_profit_pct:.2f}% profit)"
                )
        
        # Sort by profitability
        opportunities.sort(key=lambda x: x.net_profit_pct, reverse=True)
        
        logger.info(f"Found {len(opportunities)} profitable opportunities")
        return opportunities
    
    def _analyze_market(self, market: Market) -> Optional[ArbitrageOpportunity]:
        """
        Analyze a single market for arbitrage.
        
        The key insight:
        - If you buy $1 worth of each outcome, one MUST pay out $1
        - If total cost < $1, you profit
        - Example: YES=40¢, NO=55¢ → Cost=95¢, Payout=$1, Profit=5¢
        """
        if market.closed or not market.active:
            return None
        
        if len(market.outcome_prices) < 2:
            return None
        
        # Calculate total cost to buy all outcomes
        total_cost = sum(market.outcome_prices)
        
        # No arbitrage if total cost >= 1
        if total_cost >= 1.0:
            return None
        
        # Calculate profits
        # Gross profit: (1 - total_cost) / total_cost
        gross_profit_pct = ((1.0 - total_cost) / total_cost) * 100
        
        # Net profit after fees
        # Fee is charged on winnings, which is (1/total_cost - 1) per dollar invested
        # Net = Gross - Fee on payout
        payout_per_dollar = 1.0 / total_cost
        fee_pct = config.TRADING_FEE * payout_per_dollar * 100
        net_profit_pct = gross_profit_pct - fee_pct
        
        # Calculate optimal allocation
        # To guarantee $1 payout, bet proportionally to each outcome's price
        optimal_allocation = {}
        for i, outcome in enumerate(market.outcomes):
            # Allocation ratio = price / total_cost
            optimal_allocation[outcome] = market.outcome_prices[i] / total_cost
        
        # Determine type
        arb_type = "binary" if len(market.outcomes) == 2 else "multi_outcome"
        
        return ArbitrageOpportunity(
            market=market,
            type=arb_type,
            total_cost=total_cost,
            gross_profit_pct=gross_profit_pct,
            net_profit_pct=net_profit_pct,
            optimal_allocation=optimal_allocation
        )
    
    def display_opportunities(self, opportunities: list[ArbitrageOpportunity]):
        """Display opportunities in a nice table."""
        if not opportunities:
            self.console.print("[yellow]No arbitrage opportunities found.[/yellow]")
            return
        
        table = Table(title="🎯 Arbitrage Opportunities", show_header=True)
        table.add_column("Market", style="cyan", max_width=40)
        table.add_column("Type", style="white")
        table.add_column("Total Cost", justify="right")
        table.add_column("Gross %", justify="right", style="green")
        table.add_column("Net %", justify="right", style="bold green")
        table.add_column("$100 Profit", justify="right", style="yellow")
        
        for opp in opportunities:
            # Calculate profit on $100 investment
            returns = opp.calculate_returns(100)
            
            table.add_row(
                opp.market.question[:40] + "...",
                opp.type,
                f"{opp.total_cost:.4f}",
                f"{opp.gross_profit_pct:.2f}%",
                f"{opp.net_profit_pct:.2f}%",
                f"${returns['net_profit']:.2f}"
            )
        
        self.console.print(table)
    
    def display_opportunity_details(self, opp: ArbitrageOpportunity, investment: float = 100):
        """Display detailed breakdown of an opportunity."""
        returns = opp.calculate_returns(investment)
        
        self.console.print(f"\n[bold cyan]═══ {opp.market.question} ═══[/bold cyan]\n")
        
        # Prices table
        price_table = Table(show_header=True, title="Outcome Prices")
        price_table.add_column("Outcome")
        price_table.add_column("Price", justify="right")
        price_table.add_column("Allocation", justify="right")
        price_table.add_column("Bet Amount", justify="right")
        
        for i, outcome in enumerate(opp.market.outcomes):
            price = opp.market.outcome_prices[i]
            allocation = opp.optimal_allocation[outcome]
            bet = returns['allocations'][outcome]
            
            price_table.add_row(
                outcome,
                f"${price:.4f}",
                f"{allocation*100:.1f}%",
                f"${bet:.2f}"
            )
        
        self.console.print(price_table)
        
        # Returns breakdown
        self.console.print(f"\n[bold]Investment Breakdown:[/bold]")
        self.console.print(f"  Total Investment: ${returns['investment']:.2f}")
        self.console.print(f"  Total Cost Ratio: {opp.total_cost:.4f}")
        self.console.print(f"  Guaranteed Return: ${returns['guaranteed_return']:.2f}")
        self.console.print(f"  Gross Profit: ${returns['gross_profit']:.2f}")
        self.console.print(f"  Platform Fee ({config.TRADING_FEE*100}%): -${returns['fee']:.2f}")
        self.console.print(f"  [bold green]Net Profit: ${returns['net_profit']:.2f} ({returns['roi_pct']:.2f}%)[/bold green]")


# Singleton scanner instance
scanner = ArbitrageScanner()


if __name__ == "__main__":
    # Test the scanner
    from rich import print as rprint
    
    rprint("[bold]🔍 Starting Arbitrage Scanner...[/bold]\n")
    
    scanner = ArbitrageScanner()
    opportunities = scanner.scan(limit=50)
    
    scanner.display_opportunities(opportunities)
    
    if opportunities:
        rprint("\n[bold]📊 Detailed Analysis of Best Opportunity:[/bold]")
        scanner.display_opportunity_details(opportunities[0], investment=100)

