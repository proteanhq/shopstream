Feature: Delivery exception
  A shipped package encounters a delivery problem and may recover.

  Scenario: Delivery exception during transit
    Given an in-transit fulfillment
    When a delivery exception is recorded with reason "Customer not available" at "Columbus, OH"
    Then the fulfillment status is "Exception"
    And a DeliveryException event is raised

  Scenario: Exception followed by successful delivery
    Given a fulfillment with a delivery exception
    When a tracking event "Out for Delivery" is recorded at "Columbus, OH"
    And delivery is confirmed
    Then the fulfillment status is "Delivered"
    And a DeliveryConfirmed event is raised

  Scenario: Exception reporting with location details
    Given an in-transit fulfillment
    When a delivery exception is recorded with reason "Weather delay" at "Denver, CO"
    Then the fulfillment status is "Exception"
    And the fulfillment has 2 tracking events

  Scenario: Deliver directly from exception state
    Given a fulfillment with a delivery exception
    When delivery is confirmed
    Then the fulfillment status is "Delivered"
    And a DeliveryConfirmed event is raised

  Scenario: Tracking event auto-recovers from exception
    Given a fulfillment with a delivery exception
    When a tracking event "Out for Delivery" is recorded at "Columbus, OH"
    Then the fulfillment status is "In_Transit"
    And a TrackingEventReceived event is raised

  Scenario: Cannot record exception before shipment
    Given a fulfillment in packing state
    When a delivery exception is attempted with reason "Customer not available"
    Then the fulfillment action fails with a validation error
