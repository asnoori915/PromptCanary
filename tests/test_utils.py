"""
Unit tests for utility functions.
"""

import pytest
from app.utils import (
    validate_prompt_text, 
    validate_rating, 
    validate_percentage,
    calculate_overall_score,
    round_score,
    Constants
)

class TestValidation:
    """Test validation functions."""
    
    def test_validate_prompt_text_valid(self):
        """Test valid prompt text."""
        result = validate_prompt_text("This is a valid prompt")
        assert result == "This is a valid prompt"
    
    def test_validate_prompt_text_empty(self):
        """Test empty prompt text raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_prompt_text("")
    
    def test_validate_prompt_text_too_long(self):
        """Test prompt text too long raises error."""
        long_text = "x" * (Constants.MAX_PROMPT_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            validate_prompt_text(long_text)
    
    def test_validate_rating_valid(self):
        """Test valid ratings."""
        for rating in [1, 2, 3, 4, 5]:
            assert validate_rating(rating) == rating
    
    def test_validate_rating_invalid(self):
        """Test invalid ratings raise error."""
        for rating in [0, 6, -1, 10]:
            with pytest.raises(ValueError, match="must be between 1 and 5"):
                validate_rating(rating)
    
    def test_validate_percentage_valid(self):
        """Test valid percentages."""
        for percent in [0, 50, 100]:
            assert validate_percentage(percent) == percent
    
    def test_validate_percentage_invalid(self):
        """Test invalid percentages raise error."""
        for percent in [-1, 101, 150]:
            with pytest.raises(ValueError, match="must be between 0 and 100"):
                validate_percentage(percent)

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        scores = {"clarity": 0.8, "length": 0.6, "toxicity": 1.0}
        result = calculate_overall_score(scores)
        assert result == pytest.approx(0.8, rel=1e-3)
    
    def test_calculate_overall_score_empty(self):
        """Test overall score with empty scores."""
        result = calculate_overall_score({})
        assert result == 0.0
    
    def test_round_score(self):
        """Test score rounding."""
        assert round_score(0.123456) == 0.123
        assert round_score(0.123456, 2) == 0.12
