Feature: Order cancellation
  Orders can be cancelled from early states before fulfillment begins.

  Scenario: Cancel a created order
    Given an order was created
    When the order is cancelled with reason "Changed mind" by "Customer"
    Then the order status is "Cancelled"
    And an OrderCancelled order event is raised

  Scenario: Cancel a confirmed order
    Given an order was created
    And the order was confirmed
    When the order is cancelled with reason "Changed mind" by "Customer"
    Then the order status is "Cancelled"
    And an OrderCancelled order event is raised

  Scenario: Cancel a payment pending order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    When the order is cancelled with reason "Changed mind" by "Customer"
    Then the order status is "Cancelled"
    And an OrderCancelled order event is raised

  Scenario: Cancel a paid order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    When the order is cancelled with reason "Changed mind" by "Customer"
    Then the order status is "Cancelled"
    And an OrderCancelled order event is raised

  Scenario: Cannot cancel a processing order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    When the order is cancelled with reason "Changed mind" by "Customer"
    Then the order action fails with a validation error

  Scenario: Cannot cancel a shipped order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    When the order is cancelled with reason "Changed mind" by "Customer"
    Then the order action fails with a validation error

  Scenario: Cannot cancel a delivered order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    And the order was delivered
    When the order is cancelled with reason "Changed mind" by "Customer"
    Then the order action fails with a validation error

  Scenario: Refund a cancelled order
    Given an order was created
    And the order was cancelled
    When the order is refunded
    Then the order status is "Refunded"
    And an OrderRefunded order event is raised
