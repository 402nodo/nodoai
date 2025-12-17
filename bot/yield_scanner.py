"""
Yield Farming Scanner for Polymarket
Finds "obvious" events where outcome is ~95-99% likely

Strategy:
- Find markets where YES or NO > 95%
- Buy the high-probability outcome  
- Wait for resolution, get $1.00
- Profit = (1.00 - buy_price)

Risk Levels:
- SAFE: 97%+ probability (3% max profit, low risk)
- MODERATE: 95%+ probability (5% max profit, medium risk)
- RISKY: 90%+ probability (10% max profit, high risk)
"""
import httpx
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class YieldOpportunity:
    """A yield farming opportunity."""
    market_id: str
    question: str
    outcome: str
    buy_price: float
    profit_pct: float
    days_to_resolution: int
    apy: float
    url: str
    volume: float
    risk_level: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def format_telegram(self) -> str:
        """Format for Telegram message."""
        emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(self.risk_level, "⚪")
        return (
            f"{emoji} *{self.question[:50]}*\n"
            f"   Buy {self.outcome} @ ${self.buy_price:.3f}\n"
            f"   Profit: {self.profit_pct:.2f}% | APY: {self.apy:.0f}%\n"
            f"   Days: {self.days_to_resolution} | Vol: ${self.volume:,.0f}\n"
            f"   [Open]({self.url})"
        )


class YieldScanner:
    """Scans Polymarket for yield farming opportunities."""
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    
    def __init__(
        self, 
        min_probability: float = 0.95,
        min_volume: float = 1000,
        max_days: int = 60
    ):
        self.min_probability = min_probability
        self.min_volume = min_volume
        self.max_days = max_days
        self.client = httpx.Client(timeout=30.0)
    
    def scan(self, limit: int = 300) -> List[YieldOpportunity]:
        """Scan for yield opportunities."""
        try:
            response = self.client.get(
                f"{self.GAMMA_URL}/markets",
                params={"limit": limit, "active": "true", "closed": "false"}
            )
            response.raise_for_status()
            markets = response.json()
        except Exception as e:
            print(f"Error: {e}")
            return []
        
        opportunities = []
        for market in markets:
            opp = self._analyze_market(market)
            if opp:
                opportunities.append(opp)
        
        opportunities.sort(key=lambda x: x.apy, reverse=True)
        return opportunities
    
    def _analyze_market(self, market: dict) -> Optional[YieldOpportunity]:
        """Analyze a single market."""
        try:
            # Parse data
            outcomes_raw = market.get("outcomes", '["Yes", "No"]')
            prices_raw = market.get("outcomePrices", '["0.5", "0.5"]')
            
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            prices = [float(p) for p in (json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw)]
            
            if len(outcomes) != 2:
                return None
            
            # Find high probability outcome
            yes_price, no_price = prices[0], prices[1]
            
            if yes_price >= self.min_probability:
                outcome, buy_price = "YES", yes_price
            elif no_price >= self.min_probability:
                outcome, buy_price = "NO", no_price
            else:
                return None
            
            if buy_price >= 0.995:
                return None
            
            # Volume filter
            volume = float(market.get("volume", 0))
            if volume < self.min_volume:
                return None
            
            # Calculate profit
            profit_pct = ((1.0 - buy_price) / buy_price) * 100
            
            # Days to resolution
            end_date_str = market.get("endDate")
            if not end_date_str:
                return None
            
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                days = max(1, (end_date - datetime.now(timezone.utc)).days)
            except:
                days = 30
            
            if days > self.max_days:
                return None
            
            # APY
            apy = (profit_pct / days) * 365
            
            # Risk level
            if buy_price >= 0.97:
                risk = "LOW"
            elif buy_price >= 0.95:
                risk = "MEDIUM"
            else:
                risk = "HIGH"
            
            slug = market.get("slug", market.get("id", ""))
            
            return YieldOpportunity(
                market_id=str(market.get("id", "")),
                question=market.get("question", "")[:80],
                outcome=outcome,
                buy_price=buy_price,
                profit_pct=round(profit_pct, 2),
                days_to_resolution=days,
                apy=round(apy, 1),
                url=f"https://polymarket.com/event/{slug}",
                volume=volume,
                risk_level=risk
            )
        except:
            return None
    
    def close(self):
        self.client.close()


def calculate_potential_profit(opportunities: List[YieldOpportunity], investment: float) -> dict:
    """Calculate potential profit for a given investment."""
    if not opportunities:
        return {"error": "No opportunities"}
    
    # Distribute across top 5 opportunities
    top5 = opportunities[:5]
    per_market = investment / len(top5)
    
    results = []
    total_profit = 0
    
    for opp in top5:
        shares = per_market / opp.buy_price
        profit = shares * (1.0 - opp.buy_price)
        total_profit += profit
        results.append({
            "market": opp.question[:40],
            "investment": round(per_market, 2),
            "shares": round(shares, 2),
            "profit_if_win": round(profit, 2),
            "probability": f"{opp.buy_price*100:.1f}%"
        })
    
    return {
        "total_investment": investment,
        "expected_profit": round(total_profit, 2),
        "expected_return_pct": round((total_profit / investment) * 100, 2),
        "positions": results
    }


def main():
    """CLI interface."""
    print("=" * 60)
    print("  POLYMARKET YIELD FARMING SCANNER")
    print("=" * 60)
    print()
    print("Modes:")
    print("  1. SAFE    (97%+ prob, low risk)")
    print("  2. MODERATE (95%+ prob, medium risk)")
    print("  3. RISKY   (90%+ prob, high risk)")
    print()
    
    choice = input("Select mode [1/2/3, default=2]: ").strip() or "2"
    
    thresholds = {"1": 0.97, "2": 0.95, "3": 0.90}
    modes = {"1": "SAFE", "2": "MODERATE", "3": "RISKY"}
    
    min_prob = thresholds.get(choice, 0.95)
    mode = modes.get(choice, "MODERATE")
    
    print(f"\n[*] Scanning in {mode} mode ({min_prob*100:.0f}%+ probability)...\n")
    
    scanner = YieldScanner(
        min_probability=min_prob,
        min_volume=5000,  # Min $5k volume
        max_days=30       # Max 30 days to resolution
    )
    
    opps = scanner.scan(limit=300)
    
    if not opps:
        print("[!] No opportunities found.")
        scanner.close()
        return
    
    # Filter by risk for display
    print(f"\n{'='*60}")
    print(f"  OPPORTUNITIES FOUND: {len(opps)}")
    print(f"{'='*60}\n")
    
    for i, opp in enumerate(opps[:10], 1):
        risk_emoji = {"LOW": "[SAFE]", "MEDIUM": "[MED]", "HIGH": "[RISK]"}[opp.risk_level]
        print(f"{i}. {risk_emoji} {opp.question}")
        print(f"   {opp.outcome} @ ${opp.buy_price:.3f} | Profit: {opp.profit_pct:.2f}% | APY: {opp.apy:.0f}%")
        print(f"   Days: {opp.days_to_resolution} | Volume: ${opp.volume:,.0f}")
        print(f"   {opp.url}")
        print()
    
    # Investment calculator
    print(f"{'='*60}")
    print("  INVESTMENT CALCULATOR")
    print(f"{'='*60}")
    
    try:
        amount = float(input("\nHow much to invest? [$100]: ").strip() or "100")
    except:
        amount = 100
    
    calc = calculate_potential_profit(opps, amount)
    
    print(f"\nWith ${amount:.0f} distributed across top 5 markets:")
    print(f"  Expected profit: ${calc['expected_profit']:.2f}")
    print(f"  Expected return: {calc['expected_return_pct']:.1f}%")
    print()
    
    for pos in calc["positions"]:
        print(f"  - {pos['market']}...")
        print(f"    Invest: ${pos['investment']:.0f} | Profit: ${pos['profit_if_win']:.2f} (if {pos['probability']} hits)")
    
    # Export
    print(f"\n{'='*60}")
    export = input("\nExport to JSON? [y/N]: ").strip().lower()
    if export == "y":
        data = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "opportunities": [o.to_dict() for o in opps[:20]]
        }
        with open("yield_opportunities.json", "w") as f:
            json.dump(data, f, indent=2)
        print("[+] Saved to yield_opportunities.json")
    
    scanner.close()


if __name__ == "__main__":
    main()
