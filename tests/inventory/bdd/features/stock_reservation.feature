Feature: Stock reservation
  Stock is reserved for orders, with release and confirmation.

  Scenario: Reserve stock for an order
    Given stock was initialized
    When stock is reserved for an order
    Then a StockReserved event is raised
    And the reserved quantity is 10
    And the available quantity is 90

  Scenario: Cannot reserve more than available
    Given stock was initialized
    When 200 units are reserved
    Then the action fails with a validation error

  Scenario: Release a reservation
    Given stock was initialized
    And stock was reserved
    When the reservation is released
    Then a ReservationReleased event is raised
    And the reserved quantity is 0
    And the available quantity is 100

  Scenario: Confirm a reservation
    Given stock was initialized
    And stock was reserved
    When the reservation is confirmed
    Then a ReservationConfirmed event is raised

  Scenario: Cannot release a confirmed reservation
    Given stock was initialized
    And stock was reserved
    And the reservation was confirmed
    When the reservation is released
    Then the action fails with a validation error
