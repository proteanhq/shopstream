Feature: Refund flow
  Succeeded payments can be partially or fully refunded.

  Scenario: Request a partial refund
    Given a succeeded payment of 100.00
    When a refund of 40.00 is requested for reason "Partial return"
    Then the payment has 1 refund
    And a RefundRequested payment event is raised

  Scenario: Complete a full refund
    Given a succeeded payment of 100.00
    And a refund of 100.00 was requested
    When the refund is completed with gateway ID "gw-ref-001"
    Then the payment status is "Refunded"
    And a RefundCompleted payment event is raised
