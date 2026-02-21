"""Tests for the Rating value object."""

import pytest
from protean.exceptions import ValidationError
from reviews.review.review import Rating


class TestRatingConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Rating.element_type == DomainObjects.VALUE_OBJECT

    def test_valid_rating_1(self):
        rating = Rating(score=1)
        assert rating.score == 1

    def test_valid_rating_3(self):
        rating = Rating(score=3)
        assert rating.score == 3

    def test_valid_rating_5(self):
        rating = Rating(score=5)
        assert rating.score == 5


class TestRatingBoundaries:
    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    def test_valid_scores(self, score):
        rating = Rating(score=score)
        assert rating.score == score

    def test_zero_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Rating(score=0)
        assert "Rating must be between 1 and 5" in str(exc.value)

    def test_negative_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Rating(score=-1)
        assert "Rating must be between 1 and 5" in str(exc.value)

    def test_six_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Rating(score=6)
        assert "Rating must be between 1 and 5" in str(exc.value)

    def test_large_number_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Rating(score=100)
        assert "Rating must be between 1 and 5" in str(exc.value)

    def test_missing_score_rejected(self):
        with pytest.raises(ValidationError):
            Rating()
