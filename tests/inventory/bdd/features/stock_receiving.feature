Feature: Stock receiving
  Stock is received into the warehouse, increasing on-hand quantity.

  Scenario: Receive stock into warehouse
    Given stock was initialized
    When stock is received
    Then a StockReceived event is raised
    And the on-hand quantity is 150
    And the available quantity is 150

  Scenario: Cannot receive zero quantity
    Given stock was initialized
    When zero stock is received
    Then the action fails with a validation error
