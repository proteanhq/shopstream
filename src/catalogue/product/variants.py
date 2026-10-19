"""Variant management — commands and handler."""

from typing import Any

from protean import handle
from protean.fields import Dict, Float, Identifier, String
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.product import Dimensions, Price, Product, Weight


@catalogue.command(part_of="Product")
class AddVariant:
    """Add a new purchasable variant (size, color, etc.) to a product."""

    product_id: str = Identifier(required=True)
    variant_sku: str = String(required=True, max_length=50)
    attributes: dict[str, Any] = Dict()
    base_price: float = Float(required=True)
    currency: str = String(max_length=3, default="USD")
    weight_value: float | None = Float()
    weight_unit: str | None = String(max_length=2)
    length: float | None = Float()
    width: float | None = Float()
    height: float | None = Float()
    dimension_unit: str | None = String(max_length=2)


@catalogue.command(part_of="Product")
class UpdateVariantPrice:
    """Change the base price of an existing variant."""

    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    base_price: float = Float(required=True)
    currency: str = String(max_length=3, default="USD")


@catalogue.command(part_of="Product")
class SetTierPrice:
    """Set a loyalty-tier-specific discount price on a variant."""

    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    tier: str = String(required=True, max_length=50)
    price: float = Float(required=True)


@catalogue.command_handler(part_of=Product)
class ManageVariantsHandler:
    @handle(AddVariant)
    def add_variant(self, command: AddVariant) -> None:
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)

        price = Price(
            base_price=command.base_price,
            currency=command.currency or "USD",
        )

        weight = None
        if command.weight_value is not None:
            weight = Weight(
                value=command.weight_value,
                unit=command.weight_unit or "kg",
            )

        dimensions = None
        if command.length is not None:
            dimensions = Dimensions(
                length=command.length,
                width=command.width or 0.0,
                height=command.height or 0.0,
                unit=command.dimension_unit or "cm",
            )

        product.add_variant(
            variant_sku=command.variant_sku,
            price=price,
            attributes=command.attributes,
            weight=weight,
            dimensions=dimensions,
        )
        repo.add(product)

    @handle(UpdateVariantPrice)
    def update_variant_price(self, command: UpdateVariantPrice) -> None:
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)

        new_price = Price(
            base_price=command.base_price,
            currency=command.currency or "USD",
        )
        product.update_variant_price(command.variant_id, new_price)
        repo.add(product)

    @handle(SetTierPrice)
    def set_tier_price(self, command: SetTierPrice) -> None:
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.set_tier_price(command.variant_id, command.tier, command.price)
        repo.add(product)
