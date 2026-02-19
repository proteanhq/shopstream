Feature: Order payment
  Payment flows through pending, success, and failure states.

  Scenario: Record payment pending
    Given an order was created
    And the order was confirmed
    When payment is initiated with ID "pay-001" method "credit_card"
    Then the order status is "Payment_Pending"
    And a PaymentPending order event is raised

  Scenario: Record payment success
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    When payment succeeds with ID "pay-001" amount 59.0 method "credit_card"
    Then the order status is "Paid"
    And a PaymentSucceeded order event is raised

  Scenario: Payment failure returns to Confirmed
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    When payment fails with ID "pay-001" reason "Insufficient funds"
    Then the order status is "Confirmed"
    And a PaymentFailed order event is raised

  Scenario: Cannot initiate payment on a created order
    Given an order was created
    When payment is initiated with ID "pay-001" method "credit_card"
    Then the order action fails with a validation error

  Scenario: Cannot pay an already paid order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    When payment succeeds with ID "pay-002" amount 59.0 method "credit_card"
    Then the order action fails with a validation error
