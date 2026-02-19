Feature: Customer Tier Management
  Customers can be upgraded through loyalty tiers: Standard, Silver, Gold, Platinum.
  Tier downgrades are not allowed.

  Background:
    Given a registered customer

  Scenario Outline: Upgrade customer tier
    Given the customer tier is "<current_tier>"
    When the customer is upgraded to "<new_tier>"
    Then the customer tier is "<new_tier>"
    And a TierUpgraded event is raised

    Examples:
      | current_tier | new_tier |
      | Standard     | Silver   |
      | Standard     | Gold     |
      | Standard     | Platinum |
      | Silver       | Gold     |
      | Silver       | Platinum |
      | Gold         | Platinum |

  Scenario Outline: Cannot downgrade customer tier
    Given the customer tier is "<current_tier>"
    When the customer is upgraded to "<new_tier>"
    Then the action fails with a validation error

    Examples:
      | current_tier | new_tier |
      | Silver       | Standard |
      | Gold         | Standard |
      | Gold         | Silver   |
      | Platinum     | Standard |
      | Platinum     | Silver   |
      | Platinum     | Gold     |

  Scenario: Cannot upgrade to same tier
    When the customer is upgraded to "Standard"
    Then the action fails with a validation error

  Scenario: TierUpgraded event contains previous and new tier
    When the customer is upgraded to "Gold"
    Then the TierUpgraded event contains previous tier "Standard"
    And the TierUpgraded event contains new tier "Gold"
