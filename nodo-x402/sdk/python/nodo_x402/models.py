"""
NODO x402 SDK Models
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class AIModelResult:
    """Single AI model result."""
    name: str
    action: str
    confidence: int
    reasoning: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AIModelResult":
        return cls(
            name=data.get("name", ""),
            action=data.get("action", ""),
            confidence=data.get("confidence", 0),
            reasoning=data.get("reasoning"),
        )


@dataclass
class Dissent:
    """Dissenting opinion."""
    model: str
    action: str
    reason: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Dissent":
        return cls(
            model=data.get("model", ""),
            action=data.get("action", ""),
            reason=data.get("reason", ""),
        )


@dataclass
class AnalysisResult:
    """Result from AI analysis."""
    consensus: str
    agreement: str
    confidence: int
    action: str
    potential_profit: Optional[str]
    apy: Optional[str]
    models: List[AIModelResult]
    dissent: Optional[Dissent]
    risks: List[str]
    market_question: str
    market_url: str
    yes_price: float
    no_price: float
    request_id: str
    cost: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AnalysisResult":
        analysis = data.get("analysis", {})
        market = data.get("market", {})
        meta = data.get("meta", {})
        
        models = [AIModelResult.from_dict(m) for m in data.get("models", [])]
        dissent = Dissent.from_dict(data["dissent"]) if data.get("dissent") else None
        
        return cls(
            consensus=analysis.get("consensus", ""),
            agreement=analysis.get("agreement", ""),
            confidence=analysis.get("confidence", 0),
            action=analysis.get("action", ""),
            potential_profit=analysis.get("potential_profit"),
            apy=analysis.get("apy"),
            models=models,
            dissent=dissent,
            risks=data.get("risks", []),
            market_question=market.get("question", ""),
            market_url=market.get("url", ""),
            yes_price=market.get("yes_price", 0.5),
            no_price=market.get("no_price", 0.5),
            request_id=meta.get("request_id", ""),
            cost=meta.get("cost", ""),
        )


@dataclass
class YieldOpportunity:
    """Yield farming opportunity."""
    market_id: str
    question: str
    outcome: str
    buy_price: float
    profit_pct: float
    apy: float
    days_to_resolution: int
    volume: float
    risk_level: str
    url: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> "YieldOpportunity":
        return cls(
            market_id=data.get("market_id", ""),
            question=data.get("question", ""),
            outcome=data.get("outcome", ""),
            buy_price=data.get("buy_price", 0),
            profit_pct=data.get("profit_pct", 0),
            apy=data.get("apy", 0),
            days_to_resolution=data.get("days_to_resolution", 0),
            volume=data.get("volume", 0),
            risk_level=data.get("risk_level", ""),
            url=data.get("url", ""),
        )


@dataclass
class DeltaMarket:
    """Market in delta opportunity."""
    question: str
    yes_price: float
    no_price: float
    url: str
    threshold: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DeltaMarket":
        return cls(
            question=data.get("question", ""),
            yes_price=data.get("yes_price", 0),
            no_price=data.get("no_price", 0),
            url=data.get("url", ""),
            threshold=data.get("threshold"),
        )


@dataclass
class DeltaOpportunity:
    """Delta neutral / mispricing opportunity."""
    topic: str
    logic_error: str
    profit_potential: float
    confidence: int
    action: str
    explanation: str
    event_a: DeltaMarket
    event_b: DeltaMarket
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DeltaOpportunity":
        return cls(
            topic=data.get("topic", ""),
            logic_error=data.get("logic_error", ""),
            profit_potential=data.get("profit_potential", 0),
            confidence=data.get("confidence", 0),
            action=data.get("action", ""),
            explanation=data.get("explanation", ""),
            event_a=DeltaMarket.from_dict(data.get("event_a", {})),
            event_b=DeltaMarket.from_dict(data.get("event_b", {})),
        )


@dataclass
class Market:
    """Prediction market."""
    id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    platform: str
    url: str
    liquidity: Optional[float] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Market":
        return cls(
            id=data.get("id", ""),
            question=data.get("question", ""),
            yes_price=data.get("yes_price", 0.5),
            no_price=data.get("no_price", 0.5),
            volume=data.get("volume", 0),
            platform=data.get("platform", ""),
            url=data.get("url", ""),
            liquidity=data.get("liquidity"),
            end_date=data.get("end_date"),
            category=data.get("category"),
        )


