Feature: Order confirmation
  Created orders can be confirmed to lock in the purchase.

  Scenario: Confirm a created order
    Given an order was created
    When the order is confirmed
    Then the order status is "Confirmed"
    And an OrderConfirmed order event is raised

  Scenario: Cannot confirm an already confirmed order
    Given an order was created
    And the order was confirmed
    When the order is confirmed
    Then the order action fails with a validation error

  Scenario: Cannot confirm a paid order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    When the order is confirmed
    Then the order action fails with a validation error
