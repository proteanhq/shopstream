Feature: Order creation
  Orders are created from checkout data with items, addresses, and pricing.

  Scenario: Create an order with one item
    When a new order is created with one item
    Then the order status is "Created"
    And an OrderCreated order event is raised

  Scenario: Order has correct customer ID
    When a new order is created with one item
    Then the order customer ID is "cust-001"

  Scenario: Order has correct pricing
    When a new order is created with one item
    Then the order subtotal is 50.0
    And the order grand total is 59.0

  Scenario: Order has items
    When a new order is created with one item
    Then the order has 1 item

  Scenario: Order has a created_at timestamp
    When a new order is created with one item
    Then the order has a created_at timestamp
