Feature: Stock damage
  Tracking and writing off damaged stock.

  Scenario: Mark stock as damaged
    Given stock was initialized
    When stock is marked as damaged
    Then a StockMarkedDamaged event is raised
    And the on-hand quantity is 95
    And the damaged quantity is 5
    And the available quantity is 95

  Scenario: Write off damaged stock
    Given stock was initialized
    And stock was marked damaged
    When damaged stock is written off
    Then a DamagedStockWrittenOff event is raised
    And the damaged quantity is 2

  Scenario: Cannot damage more than unreserved stock
    Given stock was initialized
    And stock was reserved
    When 95 units are marked damaged
    Then the action fails with a validation error
