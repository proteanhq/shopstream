Feature: Cart item management
  Items can be added, updated, and removed from active carts.

  Scenario: Add item to empty cart
    Given an active cart
    When an item is added to the cart with product "prod-001" variant "var-001" quantity 2
    Then the cart has 1 item
    And a CartItemAdded cart event is raised

  Scenario: Add same product merges quantities
    Given an active cart
    And the cart has an item
    When an item is added to the cart with product "prod-001" variant "var-001" quantity 3
    Then the cart has 1 item

  Scenario: Add different product creates new item
    Given an active cart
    And the cart has an item
    When an item is added to the cart with product "prod-002" variant "var-002" quantity 1
    Then the cart has 2 items

  Scenario: Update item quantity
    Given an active cart
    And the cart has an item
    When the cart item quantity is updated to 5
    Then a CartQuantityUpdated cart event is raised

  Scenario: Remove item from cart
    Given an active cart
    And the cart has an item
    When the cart item is removed
    Then the cart has 0 items
    And a CartItemRemoved cart event is raised

  Scenario: Cannot add item to converted cart
    Given an active cart
    And the cart has an item
    And the cart is converted
    When an item is added to the cart with product "prod-002" variant "var-002" quantity 1
    Then the cart action fails with a validation error

  Scenario: Cannot add item to abandoned cart
    Given an active cart
    And the cart is abandoned
    When an item is added to the cart with product "prod-001" variant "var-001" quantity 1
    Then the cart action fails with a validation error
