# AI Models & Consensus

## Model Selection

We selected 6 AI models based on three criteria:
1. **Complementary strengths** — each model excels at different things
2. **Availability via API** — all accessible through OpenRouter
3. **Cost efficiency** — balancing quality with price

### The Six Models

| Model | Strength | Best For |
|-------|----------|----------|
| **Claude 3.5 Sonnet** | Nuanced reasoning | Complex analysis, edge cases |
| **GPT-4o** | Broad knowledge | Current events, mainstream topics |
| **Gemini Pro** | Fact-checking | Numbers, statistics, verification |
| **Llama 3.1 70B** | Unbiased | Controversial topics |
| **DeepSeek Chat** | Math/Logic | Probability calculations |
| **Mistral Large** | Balanced | Tie-breaker, European perspective |

### Why These Six?

**Claude** tends to be the most thoughtful, catching nuances others miss. When a market question has hidden assumptions or edge cases, Claude usually finds them.

**GPT-4** has the broadest training data. For markets about mainstream topics (elections, sports, celebrities), GPT-4 usually has the most relevant context.

**Gemini** is Google's model with access to current search data. Good at fact-checking specific claims and numbers.

**Llama** is open-source and trained differently. Provides a contrasting perspective, especially useful for politically sensitive topics where commercial models might be cautious.

**DeepSeek** excels at mathematical reasoning. For markets involving probabilities, statistics, or logical deduction, DeepSeek often outperforms.

**Mistral** trained in France, offers slightly different cultural perspective. Good as a tie-breaker when other models are split.

---

## The Prompt

All models receive the same standardized prompt. This ensures comparable outputs.

### Prompt Structure

```python
ANALYSIS_PROMPT = """You are analyzing a prediction market opportunity.

## Market Details
Question: {question}
YES Price: ${yes_price:.3f} ({yes_prob:.1f}% implied probability)
NO Price: ${no_price:.3f} ({no_prob:.1f}% implied probability)
Volume: ${volume:,.0f}
Days until resolution: {days_left}

## Your Task
Analyze whether this is a good trading opportunity.

## Required Response Format
ACTION: [BUY_YES / BUY_NO / HOLD / SKIP]
CONFIDENCE: [1-100]

REASONING:
[2-3 sentences explaining your analysis]

KEY_FACTORS:
- [Factor 1]
- [Factor 2]

RISKS:
- [Risk 1]
- [Risk 2]
"""
```

### Why This Format?

**Structured output** makes parsing reliable. Free-form responses would require complex NLP to extract the action and confidence.

**Explicit factors and risks** forces the model to justify its recommendation, which improves quality and enables dissent analysis.

**Numerical confidence** allows mathematical aggregation. "Very confident" can't be averaged; 85 can.

---

## Response Parsing

AI models don't always follow instructions perfectly. The parser handles variations.

### Common Variations

Models might respond with:
- `ACTION: BUY YES` (missing underscore)
- `Action: **BUY_YES**` (markdown formatting)
- `Recommendation: BUY_YES` (wrong keyword)

The parser normalizes all of these:

```python
def parse_action(self, text: str) -> str:
    # Find action line
    for line in text.split('\n'):
        if 'ACTION' in line.upper() or 'RECOMMENDATION' in line.upper():
            value = line.split(':', 1)[1].strip().upper()
            
            # Remove markdown
            value = value.replace('**', '').replace('*', '')
            
            # Normalize
            if 'YES' in value and 'BUY' in value:
                return 'BUY_YES'
            if 'NO' in value and 'BUY' in value:
                return 'BUY_NO'
            # ... etc
    
    return 'SKIP'  # Default if parsing fails
```

---

## Weighted Voting

Not all votes count equally. We weight by model strength and confidence.

### The Formula

```
vote_score = model_weight × confidence
```

Example with 3 models:

| Model | Action | Confidence | Weight | Score |
|-------|--------|------------|--------|-------|
| Claude | BUY_YES | 75 | 1.5 | 112.5 |
| GPT-4 | BUY_YES | 80 | 1.2 | 96.0 |
| Llama | SKIP | 60 | 1.0 | 60.0 |

**BUY_YES total**: 112.5 + 96.0 = 208.5
**SKIP total**: 60.0

Winner: **BUY_YES** with 78% agreement (208.5 / 268.5)

### Code Implementation

```python
def weighted_vote(self, responses: List[AIResponse]) -> str:
    scores = {}
    
    for r in responses:
        weight = self.model_weights.get(r.model, 1.0)
        score = weight * r.confidence
        scores[r.action] = scores.get(r.action, 0) + score
    
    return max(scores, key=scores.get)
```

---

## Dissent Detection

When models disagree, that's valuable information. It often indicates:
- Ambiguous situation
- Missing information
- Edge case the majority missed

### Flagging Dissent

```python
def find_dissent(self, responses: list, consensus: str) -> list:
    """Find models that disagree with consensus."""
    return [
        {
            "model": r.model,
            "action": r.action,
            "reasoning": r.reasoning
        }
        for r in responses
        if r.action != consensus
    ]
```

### How We Use Dissent

1. **Show to user**: "5/6 models recommend BUY_YES, but Claude says SKIP because..."
2. **Reduce confidence**: High dissent = lower calibrated confidence
3. **Log for analysis**: Track which models tend to be contrarian (and whether they're right)

---

## Confidence Calibration

Raw confidence from models is often overconfident. We calibrate based on agreement.

### The Problem

AI models tend to report 70-90% confidence even when they shouldn't. A single model saying "85% confident" doesn't mean much.

### The Solution

Multiply raw confidence by agreement ratio:

```python
def calibrate(self, raw_confidence: int, agreement: float) -> int:
    """
    Calibrate confidence based on consensus agreement.
    
    High agreement (>90%): Boost confidence
    Low agreement (<50%): Reduce confidence
    """
    if agreement > 0.90:
        multiplier = 1.2  # Boost
    elif agreement > 0.70:
        multiplier = 1.0  # No change
    elif agreement > 0.50:
        multiplier = 0.8  # Slight reduction
    else:
        multiplier = 0.5  # Major reduction
    
    calibrated = raw_confidence * multiplier
    return max(1, min(99, int(calibrated)))
```

### Example

- Raw confidence: 80%
- Agreement: 4/6 models agree (67%)
- Multiplier: 0.8
- Calibrated confidence: **64%**

This tells the user: "Most models agree, but there's meaningful dissent."

---

## Cost Analysis

Running 6 AI models per request costs money. Here's the breakdown:

### Per-Request Costs (approximate)

| Model | Input (500 tokens) | Output (300 tokens) | Total |
|-------|-------------------|---------------------|-------|
| Claude 3.5 | $0.0015 | $0.0045 | $0.006 |
| GPT-4o | $0.00125 | $0.003 | $0.004 |
| Gemini Pro | $0.000625 | $0.0015 | $0.002 |
| Llama 70B | $0.0004 | $0.00024 | $0.0006 |
| DeepSeek | $0.00007 | $0.000084 | $0.0002 |
| Mistral Large | $0.001 | $0.0018 | $0.003 |

**Total for 6 models: ~$0.016**

### Pricing Margins

| Tier | Price | Cost | Margin |
|------|-------|------|--------|
| Quick (1 AI) | $0.01 | $0.003 | 70% |
| Standard (3 AI) | $0.05 | $0.012 | 76% |
| Deep (6 AI) | $0.10 | $0.016 | 84% |

Higher tiers have better margins because fixed costs (API overhead, etc.) are spread across more value.

---

## Performance Tracking

Over time, we track which models are most accurate to adjust weights.

### What We Track

```python
@dataclass
class PredictionRecord:
    market_id: str
    model: str
    prediction: str  # BUY_YES, BUY_NO, etc.
    confidence: int
    timestamp: datetime
    resolved: bool = False
    correct: bool = None
```

When markets resolve, we update the record and calculate accuracy per model.

### Dynamic Weights

If a model consistently outperforms, its weight increases:

```python
def update_weights(self, accuracy_data: dict):
    """Adjust weights based on historical accuracy."""
    for model, stats in accuracy_data.items():
        if stats['total'] < 20:
            continue  # Not enough data
        
        # Accuracy of 60% -> weight multiplier of 1.2
        # Accuracy of 40% -> weight multiplier of 0.8
        multiplier = stats['accuracy'] * 2
        
        new_weight = self.base_weights[model] * multiplier
        self.weights[model] = max(0.5, min(2.0, new_weight))
```
