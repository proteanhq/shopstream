Feature: Payment lifecycle
  A payment goes through initiation, processing, and completion states.

  Scenario: Initiate a new payment
    When a new payment is initiated
    Then the payment status is "Pending"
    And a PaymentInitiated payment event is raised

  Scenario: Payment succeeds via webhook
    Given a new payment is initiated
    When the payment succeeds with transaction ID "txn-001"
    Then the payment status is "Succeeded"
    And a PaymentSucceeded payment event is raised

  Scenario: Payment fails via webhook
    Given a new payment is initiated
    When the payment fails with reason "Card declined"
    Then the payment status is "Failed"
    And a PaymentFailed payment event is raised
