Feature: Order lifecycle
  End-to-end order flows covering happy path and alternative paths.

  Scenario: Complete happy path
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    And the order was delivered
    When the order is completed
    Then the order status is "Completed"
    And an OrderCompleted order event is raised

  Scenario: Full return flow
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    And the order was delivered
    And a return was requested
    And the return was approved
    And the order was returned
    When the order is refunded
    Then the order status is "Refunded"

  Scenario: Cancellation and refund flow
    Given an order was created
    And the order was cancelled
    When the order is refunded
    Then the order status is "Refunded"

  Scenario: Payment retry flow
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    When payment fails with ID "pay-001" reason "Insufficient funds"
    Then the order status is "Confirmed"
