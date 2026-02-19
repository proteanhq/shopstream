Feature: Order fulfillment
  Paid orders go through processing, shipping, and delivery.

  Scenario: Mark order as processing
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    When the order is marked as processing
    Then the order status is "Processing"
    And an OrderProcessing order event is raised

  Scenario: Ship all items
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    When the order is shipped with carrier "FedEx" tracking "TRACK-001"
    Then the order status is "Shipped"
    And an OrderShipped order event is raised

  Scenario: Deliver a shipped order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    When the order is delivered
    Then the order status is "Delivered"
    And an OrderDelivered order event is raised

  Scenario: Cannot ship a created order
    Given an order was created
    When the order is shipped with carrier "FedEx" tracking "TRACK-001"
    Then the order action fails with a validation error

  Scenario: Cannot deliver an unshipped order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    When the order is delivered
    Then the order action fails with a validation error
