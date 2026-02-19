Feature: Cart lifecycle
  Carts can be created, converted to orders, or abandoned.

  Scenario: Create cart with customer ID
    When a cart is created for customer "cust-001"
    Then the cart status is "Active"

  Scenario: Create guest cart with session ID
    When a guest cart is created with session "sess-001"
    Then the cart status is "Active"

  Scenario: Convert cart to order
    Given an active cart
    And the cart has an item
    When the cart is converted to an order
    Then the cart status is "Converted"
    And a CartConverted cart event is raised

  Scenario: Cannot convert empty cart
    Given an active cart
    When the cart is converted to an order
    Then the cart action fails with a validation error

  Scenario: Abandon a cart
    Given an active cart
    When the cart is abandoned
    Then the cart status is "Abandoned"
    And a CartAbandoned cart event is raised

  Scenario: Cannot convert abandoned cart
    Given an active cart
    And the cart is abandoned
    When the cart is converted to an order
    Then the cart action fails with a validation error

  Scenario: Cannot abandon converted cart
    Given an active cart
    And the cart has an item
    And the cart is converted
    When the cart is abandoned
    Then the cart action fails with a validation error

  Scenario: Merge guest cart items
    Given an active cart
    When guest cart items are merged with product "prod-099" variant "var-099" quantity 3
    Then the cart has 1 item
    And a CartsMerged cart event is raised
