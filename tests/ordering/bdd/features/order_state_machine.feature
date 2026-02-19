Feature: Order state machine
  Terminal states block all further transitions.

  Scenario: Cannot confirm a completed order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    And the order was delivered
    And the order was completed
    When the order is confirmed
    Then the order action fails with a validation error

  Scenario: Cannot transition from Refunded
    Given an order was created
    And the order was cancelled
    And the order was refunded
    When the order is confirmed
    Then the order action fails with a validation error
