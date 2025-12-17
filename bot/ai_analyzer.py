"""
AI Analyzer - Real AI analysis using OpenRouter
"""
import os
import httpx
from typing import Optional
from dataclasses import dataclass

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/devstral-2512:free"


@dataclass
class AIAnalysis:
    verdict: str
    confidence: int
    reasons: list[str]
    risks: list[str]
    recommendation: str


class AIAnalyzer:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def analyze(
        self,
        question: str,
        outcome: str,
        price: float,
        days_left: int,
        volume: float
    ) -> Optional[AIAnalysis]:
        if not OPENROUTER_API_KEY:
            return None
        
        prob = price * 100
        profit = ((1 - price) / price) * 100
        
        prompt = f"""Analyze this prediction market opportunity:

EVENT: {question}
BET: Buy "{outcome}" at ${price:.2f} ({prob:.0f}% probability)
POTENTIAL PROFIT: {profit:.1f}%
DAYS LEFT: {days_left}
VOLUME: ${volume:,.0f}

Give a SHORT analysis (max 200 words). Format EXACTLY like this:

VERDICT: [Is this a good bet? Why? 1-2 sentences]
CONFIDENCE: [number 1-100]
WHY IT WORKS:
- [reason 1]
- [reason 2]
- [reason 3]
RISKS:
- [risk 1]
- [risk 2]
ACTION: [BUY or SKIP] - [brief reason]"""

        try:
            response = await self.client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nodo.app",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 800
                }
            )
            
            if response.status_code != 200:
                print(f"AI API Error: {response.status_code} - {response.text[:200]}")
                return None
            
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            print(f"AI Response:\n{text}\n")  # Debug
            
            return self._parse_response(text)
            
        except Exception as e:
            print(f"AI Error: {e}")
            return None
    
    def _parse_response(self, text: str) -> AIAnalysis:
        import re
        
        # Clean markdown
        text = text.replace('**', '').replace('*', '')
        lines = text.strip().split('\n')
        
        verdict = ""
        confidence = 70
        reasons = []
        risks = []
        recommendation = ""
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower = line.lower()
            
            # Detect sections
            if 'verdict' in lower and ':' in line:
                verdict = line.split(':', 1)[1].strip()
                current_section = 'verdict'
                continue
            elif 'confidence' in lower:
                nums = re.findall(r'\d+', line)
                if nums:
                    confidence = min(100, max(1, int(nums[0])))
                current_section = None
                continue
            elif 'why it works' in lower or 'reasons' in lower:
                current_section = 'reasons'
                continue
            elif 'risk' in lower and 'action' not in lower:
                current_section = 'risks'
                continue
            elif 'action' in lower and ':' in line:
                recommendation = line.split(':', 1)[1].strip()
                current_section = None
                continue
            
            # Collect bullet points
            if line.startswith('-') or line.startswith('•'):
                item = line.lstrip('-•* ').strip()
                # Remove bold markers from start
                item = re.sub(r'^\w+\*\*:?\s*', '', item)
                
                if current_section == 'reasons' and len(reasons) < 3:
                    reasons.append(item[:100])
                elif current_section == 'risks' and len(risks) < 2:
                    risks.append(item[:100])
        
        # Defaults
        if not verdict:
            verdict = "Good opportunity based on market data"
        if not reasons:
            reasons = ["High market probability", "Good liquidity", "Short timeframe"]
        if not risks:
            risks = ["Market can be wrong", "Unexpected events"]
        if not recommendation:
            recommendation = "Review details above"
        
        return AIAnalysis(
            verdict=verdict[:200],
            confidence=confidence,
            reasons=reasons[:3],
            risks=risks[:2],
            recommendation=recommendation[:150]
        )
    
    async def close(self):
        await self.client.aclose()
