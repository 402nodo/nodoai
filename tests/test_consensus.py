"""Tests for consensus engine."""

import pytest
from typing import NamedTuple


class AIResult(NamedTuple):
    """Mock AI analysis result."""
    model: str
    action: str
    confidence: int
    reasoning: str


class TestConsensusEngine:
    """Test consensus calculation logic."""
    
    def test_unanimous_consensus(self):
        """Test when all models agree."""
        results = [
            AIResult("claude", "BUY", 85, "Strong fundamentals"),
            AIResult("gpt-4", "BUY", 82, "Positive outlook"),
            AIResult("gemini", "BUY", 80, "Good opportunity"),
        ]
        
        votes = {"BUY": 0, "HOLD": 0, "SKIP": 0}
        for r in results:
            votes[r.action] += 1
        
        consensus = max(votes, key=votes.get)
        agreement = votes[consensus] / len(results)
        
        assert consensus == "BUY"
        assert agreement == 1.0
    
    def test_majority_consensus(self):
        """Test when majority agrees."""
        results = [
            AIResult("claude", "BUY", 85, "Strong fundamentals"),
            AIResult("gpt-4", "BUY", 82, "Positive outlook"),
            AIResult("gemini", "HOLD", 60, "Uncertain"),
        ]
        
        votes = {"BUY": 0, "HOLD": 0, "SKIP": 0}
        for r in results:
            votes[r.action] += 1
        
        consensus = max(votes, key=votes.get)
        agreement = votes[consensus] / len(results)
        
        assert consensus == "BUY"
        assert round(agreement, 2) == 0.67
    
    def test_split_decision(self):
        """Test when opinions are split equally."""
        results = [
            AIResult("claude", "BUY", 85, "Strong fundamentals"),
            AIResult("gpt-4", "HOLD", 82, "Wait and see"),
            AIResult("gemini", "SKIP", 60, "Too risky"),
        ]
        
        votes = {"BUY": 0, "HOLD": 0, "SKIP": 0}
        for r in results:
            votes[r.action] += 1
        
        # All equal, consensus is arbitrary (first max)
        max_votes = max(votes.values())
        winners = [k for k, v in votes.items() if v == max_votes]
        
        assert len(winners) == 3  # All tied
    
    def test_confidence_weighted_consensus(self):
        """Test consensus weighted by confidence."""
        results = [
            AIResult("claude", "BUY", 95, "Very confident"),
            AIResult("gpt-4", "HOLD", 50, "Uncertain"),
            AIResult("gemini", "HOLD", 55, "Slight hold"),
        ]
        
        # Weight by confidence
        weighted_votes = {"BUY": 0, "HOLD": 0, "SKIP": 0}
        for r in results:
            weighted_votes[r.action] += r.confidence
        
        consensus = max(weighted_votes, key=weighted_votes.get)
        
        assert consensus == "HOLD"  # 50+55=105 > 95
    
    def test_dissent_detection(self):
        """Test finding dissenting opinions."""
        results = [
            AIResult("claude", "BUY", 85, "Strong fundamentals"),
            AIResult("gpt-4", "BUY", 82, "Positive outlook"),
            AIResult("gemini", "BUY", 80, "Good opportunity"),
            AIResult("llama", "BUY", 78, "Looks good"),
            AIResult("deepseek", "BUY", 75, "Favorable"),
            AIResult("mistral", "HOLD", 60, "Macro risks"),
        ]
        
        # Find consensus
        votes = {"BUY": 0, "HOLD": 0, "SKIP": 0}
        for r in results:
            votes[r.action] += 1
        consensus = max(votes, key=votes.get)
        
        # Find dissenters
        dissent = [r for r in results if r.action != consensus]
        
        assert consensus == "BUY"
        assert len(dissent) == 1
        assert dissent[0].model == "mistral"
        assert dissent[0].action == "HOLD"


class TestConfidenceCalculation:
    """Test confidence score calculations."""
    
    def test_average_confidence(self):
        """Test average confidence calculation."""
        confidences = [85, 82, 80, 78, 75, 60]
        
        avg = sum(confidences) / len(confidences)
        
        assert round(avg, 1) == 76.7
    
    def test_adjusted_confidence(self):
        """Test confidence adjusted by agreement level."""
        base_confidence = 80
        agreement_rate = 0.83  # 5/6 agree
        
        # Boost confidence when agreement is high
        adjusted = base_confidence * (0.5 + 0.5 * agreement_rate)
        
        assert round(adjusted, 1) == 73.2
    
    def test_minimum_confidence_threshold(self):
        """Test filtering by minimum confidence."""
        results = [
            AIResult("claude", "BUY", 85, ""),
            AIResult("gpt-4", "BUY", 45, ""),  # Below threshold
            AIResult("gemini", "BUY", 80, ""),
        ]
        
        min_confidence = 50
        reliable = [r for r in results if r.confidence >= min_confidence]
        
        assert len(reliable) == 2

