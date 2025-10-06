"""
Unit tests for scoring service.
"""

import pytest
from app.services.scoring import heuristic_scores

class TestHeuristicScoring:
    """Test heuristic scoring functions."""
    
    def test_length_score_optimal(self):
        """Test length score for optimal length prompt."""
        # Create prompt with ~40 words
        prompt = " ".join(["word"] * 40)
        result = heuristic_scores(prompt)
        assert result["length_score"] > 0.8  # Should be high for optimal length
    
    def test_length_score_too_short(self):
        """Test length score for very short prompt."""
        prompt = "short"
        result = heuristic_scores(prompt)
        assert result["length_score"] < 0.5  # Should be low for very short
    
    def test_length_score_too_long(self):
        """Test length score for very long prompt."""
        prompt = " ".join(["word"] * 200)
        result = heuristic_scores(prompt)
        assert result["length_score"] < 0.5  # Should be low for very long
    
    def test_clarity_score_no_vague_terms(self):
        """Test clarity score with no vague terms."""
        prompt = "Write a clear and specific story about a robot"
        result = heuristic_scores(prompt)
        assert result["clarity_score"] == 1.0  # Should be perfect
    
    def test_clarity_score_with_vague_terms(self):
        """Test clarity score with vague terms."""
        prompt = "Maybe write sort of a story, roughly about a robot"
        result = heuristic_scores(prompt)
        assert result["clarity_score"] < 1.0  # Should be penalized
    
    def test_toxicity_score_placeholder(self):
        """Test toxicity score (currently placeholder)."""
        prompt = "Any prompt text"
        result = heuristic_scores(prompt)
        assert result["toxicity_score"] == 1.0  # Currently always 1.0
    
    def test_all_scores_present(self):
        """Test that all expected scores are present."""
        prompt = "Test prompt"
        result = heuristic_scores(prompt)
        expected_keys = ["length_score", "clarity_score", "toxicity_score"]
        for key in expected_keys:
            assert key in result
            assert 0.0 <= result[key] <= 1.0  # Scores should be in [0,1] range
    
    def test_scores_are_rounded(self):
        """Test that scores are properly rounded."""
        prompt = "Test prompt"
        result = heuristic_scores(prompt)
        for score in result.values():
            # Check that score has at most 3 decimal places
            assert len(str(score).split('.')[-1]) <= 3
