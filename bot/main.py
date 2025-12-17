"""
Nodo - Intra-Platform Arbitrage Bot
Main entry point and bot loop.
"""
import time
import sys
import os
from datetime import datetime
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.layout import Layout

from config import config
from polymarket_client import PolymarketClient
from arbitrage_scanner import ArbitrageScanner, ArbitrageOpportunity

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8')


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level=config.LOG_LEVEL
)
logger.add(
    "logs/nodo_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


class NodoBot:
    """
    Main bot class that orchestrates scanning and (eventually) execution.
    """
    
    def __init__(self):
        self.console = Console()
        self.client = PolymarketClient()
        self.scanner = ArbitrageScanner(self.client)
        self.running = False
        self.scan_count = 0
        self.opportunities_found = 0
        self.best_opportunity: ArbitrageOpportunity | None = None
        
    def print_banner(self):
        """Print startup banner."""
        banner = """
    _   _  ____  _____   ____  
   | \ | |/ __ \|  __ \ / __ \ 
   |  \| | |  | | |  | | |  | |
   | . ` | |  | | |  | | |  | |
   | |\  | |__| | |__| | |__| |
   |_| \_|\____/|_____/ \____/ 
    
    Intra-Platform Arbitrage Bot v0.1.0
    """
        self.console.print(Panel(banner, style="bold cyan", border_style="cyan"))
        
    def print_config(self):
        """Print current configuration."""
        table = Table(title="⚙️ Configuration", show_header=False)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("API URL", config.POLYMARKET_API_URL)
        table.add_row("Min Profit Threshold", f"{config.MIN_PROFIT_THRESHOLD}%")
        table.add_row("Max Position Size", f"${config.MAX_POSITION_SIZE}")
        table.add_row("Scan Interval", f"{config.SCAN_INTERVAL}s")
        table.add_row("Trading Fee", f"{config.TRADING_FEE * 100}%")
        
        self.console.print(table)
        self.console.print()
    
    def generate_status_table(self) -> Table:
        """Generate real-time status table."""
        table = Table(title="📊 Bot Status", show_header=False, expand=True)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        table.add_row("Status", "[green]RUNNING[/green]" if self.running else "[red]STOPPED[/red]")
        table.add_row("Scans Completed", str(self.scan_count))
        table.add_row("Opportunities Found", str(self.opportunities_found))
        table.add_row("Last Scan", datetime.now().strftime("%H:%M:%S"))
        
        if self.best_opportunity:
            table.add_row("", "")
            table.add_row("[bold]Best Opportunity[/bold]", "")
            table.add_row("Market", self.best_opportunity.market.question[:35] + "...")
            table.add_row("Net Profit", f"[green]{self.best_opportunity.net_profit_pct:.2f}%[/green]")
        
        return table
    
    def scan_once(self) -> list[ArbitrageOpportunity]:
        """Perform a single scan."""
        self.scan_count += 1
        logger.info(f"Scan #{self.scan_count} starting...")
        
        opportunities = self.scanner.scan(limit=100)
        
        if opportunities:
            self.opportunities_found += len(opportunities)
            self.best_opportunity = opportunities[0]
            
            # Display opportunities
            self.console.print()
            self.scanner.display_opportunities(opportunities[:5])  # Top 5
            
            # Show detailed analysis of best one
            if opportunities[0].net_profit_pct > 1.0:  # If >1% profit
                self.console.print()
                self.scanner.display_opportunity_details(opportunities[0])
        else:
            logger.info("No profitable opportunities found in this scan")
        
        return opportunities
    
    def run_continuous(self):
        """Run the bot continuously."""
        self.running = True
        self.print_banner()
        self.print_config()
        
        self.console.print("[bold green]🚀 Starting continuous scanning...[/bold green]")
        self.console.print(f"[dim]Scanning every {config.SCAN_INTERVAL} seconds. Press Ctrl+C to stop.[/dim]\n")
        
        try:
            while self.running:
                try:
                    self.scan_once()
                    
                    # Wait for next scan
                    logger.info(f"Waiting {config.SCAN_INTERVAL}s until next scan...")
                    time.sleep(config.SCAN_INTERVAL)
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f"Error during scan: {e}")
                    time.sleep(5)  # Wait before retrying
                    
        except KeyboardInterrupt:
            self.running = False
            self.console.print("\n[yellow]🛑 Bot stopped by user[/yellow]")
            self.print_summary()
    
    def run_once(self):
        """Run a single scan and exit."""
        self.print_banner()
        self.print_config()
        
        self.console.print("[bold]🔍 Running single scan...[/bold]\n")
        opportunities = self.scan_once()
        
        self.print_summary()
        return opportunities
    
    def print_summary(self):
        """Print session summary."""
        self.console.print("\n")
        table = Table(title="📈 Session Summary", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Total Scans", str(self.scan_count))
        table.add_row("Total Opportunities", str(self.opportunities_found))
        
        if self.best_opportunity:
            table.add_row("Best Profit Found", f"{self.best_opportunity.net_profit_pct:.2f}%")
            table.add_row("Best Market", self.best_opportunity.market.question[:40])
        
        self.console.print(table)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nodo - Prediction Market Arbitrage Bot")
    parser.add_argument(
        "--once", "-o",
        action="store_true",
        help="Run a single scan and exit"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=None,
        help="Override scan interval (seconds)"
    )
    
    args = parser.parse_args()
    
    # Override config if specified
    if args.interval:
        config.SCAN_INTERVAL = args.interval
    
    # Create and run bot
    bot = NodoBot()
    
    if args.once:
        bot.run_once()
    else:
        bot.run_continuous()


if __name__ == "__main__":
    main()

