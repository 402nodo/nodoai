"""
AI Orchestrator Service
Multi-model consensus analysis for prediction markets.

Supports 6 AI models for deep analysis:
1. Claude Opus (Anthropic) - Best for reasoning
2. GPT-4o (OpenAI) - Best for general analysis  
3. Gemini Pro (Google) - Best for data synthesis
4. Llama 405B (Meta) - Open source alternative
5. DeepSeek (DeepSeek) - Financial focus
6. Mistral Large (Mistral) - European perspective
"""
import asyncio
import uuid
import time
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

import httpx
from loguru import logger

from src.config import settings


class AnalysisTier(Enum):
    """
    Analysis tiers with different model counts.
    
    - QUICK ($0.01): 1 model, ~2s - Fast single check
    - STANDARD ($0.05): 3 models, ~5s - Balanced analysis
    - DEEP ($0.10): 6 models, ~10s - Full consensus
    """
    QUICK = 1      # 1 model (fastest)
    STANDARD = 3   # 3 models (balanced)
    DEEP = 6       # 6 models (full consensus)


@dataclass
class AIModelConfig:
    """Configuration for an AI model."""
    name: str
    provider: str  # anthropic, openai, google, openrouter
    model_id: str
    api_key_setting: str
    description: str = ""


# Available AI models - ordered by priority for tier selection
AI_MODELS = [
    AIModelConfig(
        name="claude-opus",
        provider="anthropic",
        model_id="claude-3-opus-20240229",
        api_key_setting="anthropic_api_key",
        description="Best for complex reasoning and nuanced analysis"
    ),
    AIModelConfig(
        name="gpt-4o",
        provider="openai",
        model_id="gpt-4o",
        api_key_setting="openai_api_key",
        description="Best for general analysis and market understanding"
    ),
    AIModelConfig(
        name="gemini-pro",
        provider="google",
        model_id="gemini-1.5-pro",
        api_key_setting="google_api_key",
        description="Best for data synthesis and pattern recognition"
    ),
    AIModelConfig(
        name="llama-405b",
        provider="openrouter",
        model_id="meta-llama/llama-3.1-405b-instruct",
        api_key_setting="openrouter_api_key",
        description="Open source, alternative perspective"
    ),
    AIModelConfig(
        name="deepseek-v3",
        provider="openrouter",
        model_id="deepseek/deepseek-chat",
        api_key_setting="openrouter_api_key",
        description="Financial and quantitative focus"
    ),
    AIModelConfig(
        name="mistral-large",
        provider="openrouter",
        model_id="mistralai/mistral-large-latest",
        api_key_setting="openrouter_api_key",
        description="European perspective, multilingual"
    ),
]


class AIOrchestrator:
    """
    Orchestrates multi-model AI analysis.
    
    Sends the same market to multiple AI models in parallel,
    then aggregates their responses into a consensus verdict.
    
    Tier Model Selection:
    - QUICK (1): Claude Opus only
    - STANDARD (3): Claude + GPT-4 + Gemini
    - DEEP (6): All 6 models
    """
    
    # API endpoints
    ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
    OPENAI_URL = "https://api.openai.com/v1/chat/completions"
    GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def analyze(
        self,
        market_url: str,
        strategy: str = "yield_farming",
        tier: AnalysisTier = AnalysisTier.STANDARD,
    ) -> Dict[str, Any]:
        """
        Analyze a market using multiple AI models.
        
        Args:
            market_url: URL or ID of the market
            strategy: Analysis strategy (yield_farming, delta_neutral, momentum)
            tier: Analysis tier (determines number of models)
            
        Returns:
            Consensus analysis result
        """
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        logger.info(f"[{request_id}] Starting {tier.name} analysis for {market_url}")
        
        # Fetch market data
        market = await self._fetch_market(market_url)
        
        if not market:
            return {
                "error": "Failed to fetch market data",
                "meta": {"request_id": request_id}
            }
        
        # Select models based on tier
        models = AI_MODELS[:tier.value]
        
        # Run parallel analysis
        tasks = [
            self._analyze_with_model(model, market, strategy)
            for model in models
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        model_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Model {models[i].name} failed: {result}")
            elif result:
                model_results.append(result)
        
        # Build consensus
        consensus = self._build_consensus(model_results)
        
        # Find dissent
        dissent = self._find_dissent(model_results, consensus["action"])
        
        processing_time = time.time() - start_time
        
        return {
            "market": market,
            "consensus": consensus,
            "models": model_results,
            "dissent": dissent,
            "risks": self._generate_risks(market, consensus),
            "meta": {
                "request_id": request_id,
                "processing_time": f"{processing_time:.1f}s",
                "models_used": len(model_results),
                "tier": tier.name.lower()
            }
        }
    
    async def _fetch_market(self, market_url: str) -> Optional[Dict]:
        """Fetch market data from Polymarket."""
        try:
            # Parse market URL/ID
            if "polymarket.com" in market_url:
                slug = market_url.split("/")[-1]
            else:
                slug = market_url
            
            # Fetch from Gamma API
            response = await self.client.get(
                "https://gamma-api.polymarket.com/markets",
                params={"slug": slug, "limit": 1}
            )
            
            if response.status_code != 200:
                # Try as condition ID
                response = await self.client.get(
                    f"https://gamma-api.polymarket.com/markets/{slug}"
                )
            
            if response.status_code == 200:
                data = response.json()
                market = data[0] if isinstance(data, list) else data
                
                import json
                prices = market.get("outcomePrices", '["0.5", "0.5"]')
                if isinstance(prices, str):
                    prices = json.loads(prices)
                
                return {
                    "id": market.get("id"),
                    "question": market.get("question", "Unknown"),
                    "yes_price": float(prices[0]),
                    "no_price": float(prices[1]),
                    "volume": float(market.get("volume", 0)),
                    "end_date": market.get("endDate"),
                    "url": f"https://polymarket.com/event/{market.get('slug', slug)}"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch market: {e}")
            return None
    
    async def _analyze_with_model(
        self,
        model: AIModelConfig,
        market: Dict,
        strategy: str
    ) -> Optional[Dict]:
        """
        Analyze market with a single AI model.
        
        Routes to appropriate API based on provider:
        - anthropic -> Anthropic API (Claude)
        - openai -> OpenAI API (GPT-4)
        - google -> Google AI API (Gemini)
        - openrouter -> OpenRouter (Llama, DeepSeek, Mistral)
        """
        try:
            prompt = self._build_prompt(market, strategy)
            
            # Route to appropriate provider
            if model.provider == "anthropic":
                return await self._call_anthropic(model, prompt)
            elif model.provider == "openai":
                return await self._call_openai(model, prompt)
            elif model.provider == "google":
                return await self._call_google(model, prompt)
            else:  # openrouter
                return await self._call_openrouter(model, prompt)
                
        except Exception as e:
            logger.error(f"{model.name} error: {e}")
            return None
    
    async def _call_anthropic(self, model: AIModelConfig, prompt: str) -> Optional[Dict]:
        """Call Anthropic Claude API directly."""
        api_key = settings.anthropic_api_key
        if not api_key:
            logger.warning(f"No Anthropic API key, falling back to OpenRouter")
            return await self._call_openrouter(model, prompt)
        
        try:
            response = await self.client.post(
                self.ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model.model_id,
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Anthropic API error: {response.status_code}")
                return await self._call_openrouter(model, prompt)
            
            data = response.json()
            text = data["content"][0]["text"]
            return self._parse_model_response(model.name, text)
            
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return await self._call_openrouter(model, prompt)
    
    async def _call_openai(self, model: AIModelConfig, prompt: str) -> Optional[Dict]:
        """Call OpenAI API directly."""
        api_key = settings.openai_api_key
        if not api_key:
            logger.warning(f"No OpenAI API key, falling back to OpenRouter")
            return await self._call_openrouter(model, prompt)
        
        try:
            response = await self.client.post(
                self.OPENAI_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model.model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"OpenAI API error: {response.status_code}")
                return await self._call_openrouter(model, prompt)
            
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            return self._parse_model_response(model.name, text)
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return await self._call_openrouter(model, prompt)
    
    async def _call_google(self, model: AIModelConfig, prompt: str) -> Optional[Dict]:
        """Call Google Gemini API directly."""
        api_key = settings.google_api_key
        if not api_key:
            logger.warning(f"No Google API key, falling back to OpenRouter")
            return await self._call_openrouter(model, prompt)
        
        try:
            url = f"{self.GOOGLE_URL}/{model.model_id}:generateContent?key={api_key}"
            response = await self.client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 500
                    }
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Google API error: {response.status_code}")
                return await self._call_openrouter(model, prompt)
            
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_model_response(model.name, text)
            
        except Exception as e:
            logger.error(f"Google error: {e}")
            return await self._call_openrouter(model, prompt)
    
    async def _call_openrouter(self, model: AIModelConfig, prompt: str) -> Optional[Dict]:
        """Call OpenRouter API (fallback for all models + primary for Llama/DeepSeek/Mistral)."""
        api_key = settings.openrouter_api_key
        if not api_key:
            logger.warning(f"No OpenRouter API key for {model.name}")
            return None
        
        try:
            # Map model to OpenRouter format
            openrouter_model = model.model_id
            if model.provider == "anthropic":
                openrouter_model = f"anthropic/{model.model_id}"
            elif model.provider == "openai":
                openrouter_model = f"openai/{model.model_id}"
            elif model.provider == "google":
                openrouter_model = f"google/{model.model_id}"
            
            response = await self.client.post(
                self.OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nodo.ai",
                    "X-Title": "NODO x402"
                },
                json={
                    "model": openrouter_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"OpenRouter API error for {model.name}: {response.status_code}")
                return None
            
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            return self._parse_model_response(model.name, text)
            
        except Exception as e:
            logger.error(f"OpenRouter error for {model.name}: {e}")
            return None
    
    def _build_prompt(self, market: Dict, strategy: str) -> str:
        """Build analysis prompt for AI model."""
        prob = market["yes_price"] * 100
        
        strategy_context = {
            "yield_farming": "Focus on events with high probability (>95%) that offer safe yield.",
            "delta_neutral": "Look for logical inconsistencies and mispricing opportunities.",
            "momentum": "Analyze price momentum and sentiment shifts."
        }.get(strategy, "General market analysis.")
        
        return f"""Analyze this prediction market:

MARKET: {market['question']}
YES Price: ${market['yes_price']:.2f} ({prob:.0f}% implied probability)
NO Price: ${market['no_price']:.2f} ({100-prob:.0f}% implied probability)
Volume: ${market['volume']:,.0f}
End Date: {market.get('end_date', 'Unknown')}

Strategy: {strategy_context}

Provide a brief analysis (max 150 words) in this format:
ACTION: [BUY_YES / BUY_NO / SKIP]
CONFIDENCE: [1-100]
REASONING: [2-3 sentences explaining your decision]

Be concise and decisive."""
    
    def _parse_model_response(self, model_name: str, text: str) -> Dict:
        """Parse AI model response into structured format."""
        import re
        
        # Extract action
        action_match = re.search(r'ACTION:\s*(BUY_YES|BUY_NO|SKIP|HOLD)', text, re.IGNORECASE)
        action = action_match.group(1).upper() if action_match else "SKIP"
        
        # Extract confidence
        conf_match = re.search(r'CONFIDENCE:\s*(\d+)', text)
        confidence = int(conf_match.group(1)) if conf_match else 50
        confidence = min(100, max(1, confidence))
        
        # Extract reasoning
        reason_match = re.search(r'REASONING:\s*(.+?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)
        reasoning = reason_match.group(1).strip() if reason_match else text[:200]
        
        return {
            "model": model_name,
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning[:300]
        }
    
    def _build_consensus(self, results: List[Dict]) -> Dict:
        """Build consensus from multiple model results."""
        if not results:
            return {
                "action": "SKIP",
                "agreement": "0/0",
                "confidence": 0,
                "recommendation": "No analysis available"
            }
        
        # Vote counting with confidence weighting
        votes = {"BUY_YES": 0, "BUY_NO": 0, "SKIP": 0}
        total_confidence = 0
        
        for r in results:
            action = r["action"]
            if action in votes:
                votes[action] += r["confidence"]
            total_confidence += r["confidence"]
        
        # Find winner
        consensus_action = max(votes, key=votes.get)
        
        # Count raw agreement
        agreement_count = sum(1 for r in results if r["action"] == consensus_action)
        
        # Calculate average confidence for consensus
        consensus_results = [r for r in results if r["action"] == consensus_action]
        avg_confidence = sum(r["confidence"] for r in consensus_results) / len(consensus_results) if consensus_results else 0
        
        # Generate recommendation
        if consensus_action == "BUY_YES":
            recommendation = "Buy YES position"
        elif consensus_action == "BUY_NO":
            recommendation = "Buy NO position"
        else:
            recommendation = "Skip this market"
        
        return {
            "action": consensus_action,
            "agreement": f"{agreement_count}/{len(results)}",
            "confidence": int(avg_confidence),
            "recommendation": recommendation,
            "profit_pct": None,  # Would calculate from market data
            "apy": None
        }
    
    def _find_dissent(self, results: List[Dict], consensus_action: str) -> Optional[Dict]:
        """Find dissenting opinion if any."""
        dissenters = [r for r in results if r["action"] != consensus_action]
        
        if not dissenters:
            return None
        
        # Return highest confidence dissenter
        dissenter = max(dissenters, key=lambda x: x["confidence"])
        
        return {
            "model": dissenter["model"],
            "action": dissenter["action"],
            "reason": dissenter["reasoning"][:200]
        }
    
    def _generate_risks(self, market: Dict, consensus: Dict) -> List[str]:
        """Generate risk warnings based on analysis."""
        risks = []
        
        # General risks
        risks.append("Market sentiment can shift unexpectedly")
        
        # Low confidence risk
        if consensus["confidence"] < 60:
            risks.append(f"Low consensus confidence ({consensus['confidence']}%)")
        
        # Volume risk
        if market["volume"] < 10000:
            risks.append("Low market volume may affect liquidity")
        
        # Split consensus risk
        agreement = consensus["agreement"].split("/")
        if len(agreement) == 2:
            agree, total = int(agreement[0]), int(agreement[1])
            if agree < total * 0.6:
                risks.append("Models are split - higher uncertainty")
        
        return risks[:3]
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

