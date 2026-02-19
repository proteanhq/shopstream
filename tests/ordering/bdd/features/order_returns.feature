Feature: Order returns
  Delivered orders can go through the return flow.

  Scenario: Request return from delivered order
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    And the order was delivered
    When a return is requested with reason "Defective product"
    Then the order status is "Return_Requested"
    And a ReturnRequested order event is raised

  Scenario: Approve a return request
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    And the order was delivered
    And a return was requested
    When the return is approved
    Then the order status is "Return_Approved"
    And a ReturnApproved order event is raised

  Scenario: Record returned items
    Given an order was created
    And the order was confirmed
    And the order payment is pending
    And the order was paid
    And the order is processing
    And the order was shipped
    And the order was delivered
    And a return was requested
    And the return was approved
    When the return is recorded
    Then the order status is "Returned"
    And an OrderReturned order event is raised

  Scenario: Refund a returned order
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
    And an OrderRefunded order event is raised

  Scenario: Cannot request return from non-delivered order
    Given an order was created
    And the order was confirmed
    When a return is requested with reason "Changed mind"
    Then the order action fails with a validation error
