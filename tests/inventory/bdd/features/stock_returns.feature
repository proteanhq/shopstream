Feature: Stock returns
  Returned items are added back to on-hand inventory.

  Scenario: Return items to stock
    Given stock was initialized
    When items are returned to stock
    Then a StockReturned event is raised
    And the on-hand quantity is 110
    And the available quantity is 110

  Scenario: Cannot return zero quantity
    Given stock was initialized
    When zero items are returned
    Then the action fails with a validation error
