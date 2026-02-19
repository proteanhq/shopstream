Feature: Order modification
  Items and coupons can only be modified in Created state.

  Scenario: Add an item to a created order
    Given an order was created
    When an item is added to the order
    Then an ItemAdded order event is raised

  Scenario: Remove an item from a created order
    Given an order was created
    When an item is removed from the order
    Then an ItemRemoved order event is raised

  Scenario: Update item quantity
    Given an order was created
    When the item quantity is updated to 5
    Then an ItemQuantityUpdated order event is raised

  Scenario: Apply a coupon to a created order
    Given an order was created
    When a coupon "SAVE20" is applied
    Then a CouponApplied order event is raised

  Scenario: Cannot add item after confirmation
    Given an order was created
    And the order was confirmed
    When an item is added to the order
    Then the order action fails with a validation error

  Scenario: Cannot remove item after confirmation
    Given an order was created
    And the order was confirmed
    When an item is removed from the order
    Then the order action fails with a validation error

  Scenario: Cannot apply coupon after confirmation
    Given an order was created
    And the order was confirmed
    When a coupon "SAVE20" is applied
    Then the order action fails with a validation error
