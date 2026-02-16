"""Tests for the SEO value object."""

import pytest
from catalogue.product.product import SEO
from protean.exceptions import ValidationError


class TestSEOConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert SEO.element_type == DomainObjects.VALUE_OBJECT

    def test_valid_seo_with_all_fields(self):
        seo = SEO(
            meta_title="Great Product",
            meta_description="A wonderful product",
            slug="great-product",
        )
        assert seo.meta_title == "Great Product"
        assert seo.meta_description == "A wonderful product"
        assert seo.slug == "great-product"

    def test_valid_seo_with_only_slug(self):
        seo = SEO(slug="my-product")
        assert seo.slug == "my-product"
        assert seo.meta_title is None
        assert seo.meta_description is None


class TestSEOSlugValidation:
    @pytest.mark.parametrize(
        "slug",
        [
            "simple-product",
            "product-123",
            "a",
            "abc",
            "my-great-product-2024",
            "x" * 200,
        ],
        ids=["basic", "with-numbers", "single-char", "short", "long-slug", "max-length"],
    )
    def test_valid_slugs(self, slug):
        seo = SEO(slug=slug)
        assert seo.slug == slug

    def test_uppercase_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SEO(slug="My-Product")
        assert "lowercase" in str(exc.value)

    def test_spaces_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SEO(slug="my product")
        assert "lowercase" in str(exc.value)

    def test_underscores_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SEO(slug="my_product")
        assert "lowercase" in str(exc.value)

    def test_leading_hyphen_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SEO(slug="-my-product")
        assert "must not start or end" in str(exc.value)

    def test_trailing_hyphen_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SEO(slug="my-product-")
        assert "must not start or end" in str(exc.value)

    def test_consecutive_hyphens_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SEO(slug="my--product")
        assert "consecutive hyphens" in str(exc.value)

    def test_seo_without_slug_is_valid(self):
        seo = SEO(meta_title="Title")
        assert seo.slug is None


class TestSEOMetaFieldLengths:
    def test_meta_title_max_length(self):
        seo = SEO(meta_title="T" * 70, slug="test")
        assert len(seo.meta_title) == 70

    def test_meta_title_over_max_rejected(self):
        with pytest.raises(ValidationError):
            SEO(meta_title="T" * 71, slug="test")

    def test_meta_description_max_length(self):
        seo = SEO(meta_description="D" * 160, slug="test")
        assert len(seo.meta_description) == 160

    def test_meta_description_over_max_rejected(self):
        with pytest.raises(ValidationError):
            SEO(meta_description="D" * 161, slug="test")
