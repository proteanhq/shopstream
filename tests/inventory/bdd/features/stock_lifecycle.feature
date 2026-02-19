Feature: Stock lifecycle
  End-to-end inventory lifecycle scenarios.

  Scenario: Complete happy path - receive, reserve, confirm, commit
    Given stock was initialized
    And stock was received
    When stock is reserved for an order
    Then a StockReserved event is raised
    And the on-hand quantity is 150
    And the available quantity is 140

  Scenario: Reserve, release, reserve again
    Given stock was initialized
    And stock was reserved
    And the reservation was released
    When stock is reserved for an order
    Then a StockReserved event is raised
    And the reserved quantity is 10
    And the available quantity is 90

  Scenario: Full commitment flow
    Given stock was initialized
    And stock was reserved
    And the reservation was confirmed
    And stock was committed
    When items are returned to stock
    Then a StockReturned event is raised
    And the on-hand quantity is 100
    And the available quantity is 100
