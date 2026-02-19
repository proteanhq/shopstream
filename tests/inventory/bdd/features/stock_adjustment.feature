Feature: Stock adjustment
  Manual stock adjustments and physical counts.

  Scenario: Adjust stock down for shrinkage
    Given stock was initialized
    When stock is adjusted down
    Then a StockAdjusted event is raised
    And the on-hand quantity is 90
    And the available quantity is 90

  Scenario: Adjust stock up for correction
    Given stock was initialized
    When stock is adjusted up
    Then a StockAdjusted event is raised
    And the on-hand quantity is 110
    And the available quantity is 110

  Scenario: Cannot adjust to negative on-hand
    Given stock was initialized
    When stock is adjusted by -200
    Then the action fails with a validation error

  Scenario: Stock check with discrepancy
    Given stock was initialized
    When a stock check records 95 units
    Then a StockCheckRecorded event is raised
    And a StockAdjusted event is raised
    And the on-hand quantity is 95
