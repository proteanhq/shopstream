Feature: Product variant management
  Products have purchasable variants with SKUs and pricing.

  Background:
    Given a draft product

  Scenario: Add a variant with SKU and price
    When a variant is added with SKU "VAR-001" and price 29.99
    Then the product has 1 variant
    And a VariantAdded product event is raised

  Scenario: Add a variant with all fields
    When a variant is added with SKU "VAR-002" price 49.99 and weight 1.5
    Then the product has 1 variant
    And the variant weight is 1.5

  Scenario: Add multiple variants
    When a variant is added with SKU "VAR-001" and price 29.99
    And a variant is added with SKU "VAR-002" and price 39.99
    Then the product has 2 variants

  Scenario: Variant has correct SKU
    When a variant is added with SKU "VAR-001" and price 29.99
    Then the variant SKU is "VAR-001"
