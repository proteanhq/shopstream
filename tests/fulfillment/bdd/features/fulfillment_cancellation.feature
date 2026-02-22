Feature: Fulfillment cancellation
  Fulfillments can be cancelled before shipment but not after.

  Scenario: Cancel pending fulfillment
    Given a pending fulfillment
    When the fulfillment is cancelled with reason "Customer changed mind"
    Then the fulfillment status is "Cancelled"
    And the cancellation reason is "Customer changed mind"
    And a FulfillmentCancelled event is raised

  Scenario: Cancel during picking
    Given a fulfillment in picking state
    When the fulfillment is cancelled with reason "Out of stock"
    Then the fulfillment status is "Cancelled"
    And the cancellation reason is "Out of stock"
    And a FulfillmentCancelled event is raised

  Scenario: Cancel during packing
    Given a fulfillment in packing state
    When the fulfillment is cancelled with reason "Customer request"
    Then the fulfillment status is "Cancelled"
    And the cancellation reason is "Customer request"
    And a FulfillmentCancelled event is raised

  Scenario: Cancel ready-to-ship fulfillment
    Given a packed fulfillment with shipping label
    When the fulfillment is cancelled with reason "Address error"
    Then the fulfillment status is "Cancelled"
    And the cancellation reason is "Address error"
    And a FulfillmentCancelled event is raised

  Scenario: Cannot cancel after shipping
    Given a shipped fulfillment
    When cancellation is attempted with reason "Too late"
    Then the fulfillment action fails with a validation error

  Scenario: Cannot cancel delivered fulfillment
    Given an in-transit fulfillment
    When delivery is confirmed
    And cancellation is attempted with reason "Changed mind"
    Then the fulfillment action fails with a validation error
