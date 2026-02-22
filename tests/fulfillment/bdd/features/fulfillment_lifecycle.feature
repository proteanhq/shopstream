Feature: Fulfillment lifecycle
  A paid order moves through the warehouse pipeline: create, pick, pack, ship, deliver.

  Scenario: Happy path - create through delivery
    When a fulfillment is created for order "ord-happy-001" with 2 items
    And picker "Alice" is assigned to the fulfillment
    And all items are picked from their locations
    And the pick list is completed
    And the items are packed by "Bob" into 1 packages
    And a shipping label is generated for carrier "FedEx" with service "Standard"
    And the shipment is handed off with tracking number "FDX-789456123"
    And a tracking event "In Transit" is recorded at "Memphis, TN"
    And delivery is confirmed
    Then the fulfillment status is "Delivered"

  Scenario: Create fulfillment with valid order
    When a fulfillment is created for order "ord-create-001" with 2 items
    Then the fulfillment status is "Pending"
    And a FulfillmentCreated event is raised

  Scenario: Assign picker to pending fulfillment
    Given a pending fulfillment
    When picker "Alice" is assigned to the fulfillment
    Then the fulfillment status is "Picking"
    And the fulfillment has a pick list assigned to "Alice"
    And a PickerAssigned event is raised

  Scenario: Pick all items and complete picking
    Given a fulfillment in picking state
    When all items are picked from their locations
    And the pick list is completed
    Then the fulfillment status is "Packing"
    And all items are in Picked status
    And a PickingCompleted event is raised

  Scenario: Pack items and generate shipping label
    Given a fulfillment in packing state
    When the items are packed by "Bob" into 1 packages
    And a shipping label is generated for carrier "FedEx" with service "Standard"
    Then the fulfillment status is "Ready_To_Ship"
    And all items are in Packed status
    And the shipment carrier is "FedEx"
    And a ShippingLabelGenerated event is raised

  Scenario: Hand off to carrier and track delivery
    Given a packed fulfillment with shipping label
    When the shipment is handed off with tracking number "FDX-789456123"
    And a tracking event "In Transit" is recorded at "Memphis, TN"
    And delivery is confirmed
    Then the fulfillment status is "Delivered"
    And the tracking number is "FDX-789456123"
    And a DeliveryConfirmed event is raised

  Scenario: Cannot pack before picking is complete
    Given a fulfillment in picking state
    When packing is attempted by "Bob"
    Then the fulfillment action fails with a validation error

  Scenario: Cannot complete pick list with unpicked items
    Given a fulfillment in picking state
    When the pick list completion is attempted
    Then the fulfillment action fails with a validation error

  Scenario: Cannot generate label before packing
    Given a fulfillment in packing state
    When label generation is attempted for carrier "FedEx" with service "Standard"
    Then the fulfillment action fails with a validation error

  Scenario: Cannot assign picker to non-pending fulfillment
    Given a fulfillment in picking state
    When assigning picker "Bob" is attempted
    Then the fulfillment action fails with a validation error
