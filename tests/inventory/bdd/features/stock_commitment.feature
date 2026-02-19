Feature: Stock commitment
  Confirmed reservations are committed when orders ship.

  Scenario: Commit confirmed reservation
    Given stock was initialized
    And stock was reserved
    And the reservation was confirmed
    When stock is committed
    Then a StockCommitted event is raised
    And the on-hand quantity is 90
    And the reserved quantity is 0

  Scenario: Cannot commit unconfirmed reservation
    Given stock was initialized
    And stock was reserved
    When stock is committed
    Then the action fails with a validation error
