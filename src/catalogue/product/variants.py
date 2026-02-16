"""Variant management — commands and handler."""

import json

from protean import handle
from protean.fields import Float, Identifier, String, Text
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.product import Dimensions, Price, Product, Weight


@catalogue.command(part_of="Product")
class AddVariant:
    product_id: Identifier(required=True)
    variant_sku: String(required=True, max_length=50)
    attributes: Text()
    base_price: Float(required=True)
    currency: String(max_length=3, default="USD")
    weight_value: Float()
    weight_unit: String(max_length=2)
    length: Float()
    width: Float()
    height: Float()
    dimension_unit: String(max_length=2)


@catalogue.command(part_of="Product")
class UpdateVariantPrice:
    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    base_price: Float(required=True)
    currency: String(max_length=3, default="USD")


@catalogue.command(part_of="Product")
class SetTierPrice:
    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    tier: String(required=True, max_length=50)
    price: Float(required=True)


@catalogue.command_handler(part_of=Product)
class ManageVariantsHandler:
    @handle(AddVariant)
    def add_variant(self, command):
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

        attrs = None
        if command.attributes:
            attrs = json.loads(command.attributes)

        product.add_variant(
            variant_sku=command.variant_sku,
            price=price,
            attributes=attrs,
            weight=weight,
            dimensions=dimensions,
        )
        repo.add(product)

    @handle(UpdateVariantPrice)
    def update_variant_price(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)

        new_price = Price(
            base_price=command.base_price,
            currency=command.currency or "USD",
        )
        product.update_variant_price(command.variant_id, new_price)
        repo.add(product)

    @handle(SetTierPrice)
    def set_tier_price(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.set_tier_price(command.variant_id, command.tier, command.price)
        repo.add(product)
