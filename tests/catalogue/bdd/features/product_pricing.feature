Feature: Product pricing
  Variant prices can be updated and tier-specific pricing can be set.

  Background:
    Given a draft product with a variant

  Scenario: Update variant base price
    When the variant price is updated to 39.99
    Then the variant base price is 39.99
    And a VariantPriceChanged product event is raised

  Scenario: Set Gold tier price
    When the Gold tier price is set to 24.99
    Then the variant has a Gold tier price of 24.99
    And a TierPriceSet product event is raised

  Scenario: Tier price must be less than base price
    When the Gold tier price is set to 99.99
    Then the action fails with a validation error

  Scenario: Set multiple tier prices
    When the Gold tier price is set to 24.99
    And the Platinum tier price is set to 19.99
    Then the variant has a Gold tier price of 24.99
    And the variant has a Platinum tier price of 19.99
