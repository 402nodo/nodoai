"""
Azuro Protocol Integration
https://azuro.org - Decentralized sports betting protocol
"""
import httpx
from typing import Optional
from datetime import datetime
from loguru import logger

from .base import PredictionPlatform, PlatformMarket, PlatformOutcome, MarketCategory


class AzuroPlatform(PredictionPlatform):
    """
    Azuro - Decentralized betting protocol on multiple chains.
    Uses TheGraph for data queries.
    
    Docs: https://gem.azuro.org/hub/
    """
    
    name = "azuro"
    base_url = "https://azuro.org"
    
    # TheGraph endpoints for different chains
    SUBGRAPH_URLS = {
        "polygon": "https://thegraph.azuro.org/subgraphs/name/azuro-protocol/azuro-api-polygon-v3",
        "gnosis": "https://thegraph.azuro.org/subgraphs/name/azuro-protocol/azuro-api-gnosis-v3",
        "arbitrum": "https://thegraph.azuro.org/subgraphs/name/azuro-protocol/azuro-api-arbitrum-one-v3",
    }
    
    def __init__(self, chain: str = "polygon"):
        self.chain = chain
        self.subgraph_url = self.SUBGRAPH_URLS.get(chain, self.SUBGRAPH_URLS["polygon"])
        self.client = httpx.Client(timeout=30.0)
    
    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()
    
    @property
    def is_decentralized(self) -> bool:
        return True
    
    @property
    def trading_fee(self) -> float:
        return 0.05  # ~5% margin built into odds
    
    def get_markets(self, limit: int = 100, **kwargs) -> list[PlatformMarket]:
        """
        Fetch markets from Azuro using GraphQL.
        """
        try:
            query = """
            query GetConditions($first: Int!) {
                conditions(
                    first: $first
                    where: { status: Created }
                    orderBy: turnover
                    orderDirection: desc
                ) {
                    id
                    conditionId
                    status
                    turnover
                    game {
                        id
                        title
                        startsAt
                        sport {
                            name
                        }
                        league {
                            name
                            country {
                                name
                            }
                        }
                    }
                    outcomes {
                        id
                        outcomeId
                        currentOdds
                    }
                }
            }
            """
            
            response = self.client.post(
                self.subgraph_url,
                json={"query": query, "variables": {"first": limit}}
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"[Azuro] GraphQL errors: {data['errors']}")
                return []
            
            markets = []
            conditions = data.get("data", {}).get("conditions", [])
            
            for item in conditions:
                market = self._parse_condition(item)
                if market:
                    markets.append(market)
            
            logger.info(f"[Azuro] Fetched {len(markets)} markets")
            return markets
            
        except Exception as e:
            logger.error(f"[Azuro] Failed to fetch markets: {e}")
            return []
    
    def get_market_by_id(self, market_id: str) -> Optional[PlatformMarket]:
        """Fetch specific condition by ID."""
        try:
            query = """
            query GetCondition($id: ID!) {
                condition(id: $id) {
                    id
                    conditionId
                    status
                    turnover
                    game {
                        id
                        title
                        startsAt
                        sport { name }
                        league { name country { name } }
                    }
                    outcomes {
                        id
                        outcomeId
                        currentOdds
                    }
                }
            }
            """
            
            response = self.client.post(
                self.subgraph_url,
                json={"query": query, "variables": {"id": market_id}}
            )
            response.raise_for_status()
            data = response.json()
            
            condition = data.get("data", {}).get("condition")
            if condition:
                return self._parse_condition(condition)
            return None
            
        except Exception as e:
            logger.error(f"[Azuro] Failed to fetch market {market_id}: {e}")
            return None
    
    def search_markets(self, query: str, limit: int = 20) -> list[PlatformMarket]:
        """Search markets by team/event name."""
        # Azuro doesn't have direct search, get all and filter
        markets = self.get_markets(limit=200)
        query_lower = query.lower()
        
        matching = []
        for market in markets:
            if query_lower in market.question.lower():
                matching.append(market)
                if len(matching) >= limit:
                    break
        
        return matching
    
    def _parse_condition(self, data: dict) -> Optional[PlatformMarket]:
        """Parse Azuro condition to PlatformMarket."""
        try:
            game = data.get("game", {})
            if not game:
                return None
            
            # Build question from game info
            title = game.get("title", "Unknown Match")
            sport = game.get("sport", {}).get("name", "")
            league = game.get("league", {}).get("name", "")
            
            question = f"{title}"
            if league:
                question = f"{league}: {title}"
            
            # Parse outcomes and odds
            outcomes = []
            raw_outcomes = data.get("outcomes", [])
            
            for outcome in raw_outcomes:
                odds = float(outcome.get("currentOdds", 2.0))
                # Convert odds to probability (implied probability)
                price = 1.0 / odds if odds > 0 else 0.5
                
                outcome_name = self._get_outcome_name(outcome.get("outcomeId", ""))
                outcomes.append(PlatformOutcome(
                    name=outcome_name,
                    price=price,
                    token_id=outcome.get("id")
                ))
            
            if len(outcomes) < 2:
                return None
            
            # Parse start time as end date
            end_date = None
            if game.get("startsAt"):
                try:
                    end_date = datetime.fromtimestamp(int(game["startsAt"]))
                except:
                    pass
            
            # Volume
            volume = float(data.get("turnover", 0)) / 1e18  # Convert from wei
            
            return PlatformMarket(
                platform=self.name,
                market_id=data.get("id", data.get("conditionId", "")),
                question=question,
                description=f"{sport} - {league}",
                slug=data.get("conditionId", ""),
                url=f"https://bookmaker.xyz/events/{game.get('id', '')}",
                outcomes=outcomes,
                category=MarketCategory.SPORTS,
                volume=volume,
                end_date=end_date,
                active=data.get("status") == "Created",
                resolved=data.get("status") in ["Resolved", "Canceled"],
                keywords=self._extract_keywords(title)
            )
            
        except Exception as e:
            logger.warning(f"[Azuro] Failed to parse condition: {e}")
            return None
    
    def _get_outcome_name(self, outcome_id: str) -> str:
        """Map Azuro outcome IDs to readable names."""
        # Azuro uses numeric outcome IDs
        # Common mappings:
        # 1 = Home/Yes, 2 = Away/No, 3 = Draw
        try:
            oid = int(outcome_id) if outcome_id else 0
            if oid == 1:
                return "Home"
            elif oid == 2:
                return "Away"  
            elif oid == 3:
                return "Draw"
            else:
                return f"Outcome {oid}"
        except:
            return outcome_id or "Unknown"
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords."""
        import re
        words = re.findall(r'\b[A-Z][a-z]+\b|\b[A-Z]{2,}\b', text)
        return list(set(words))[:10]

