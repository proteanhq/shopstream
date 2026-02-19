Feature: Stock initialization
  A new inventory record is created for a product variant at a warehouse.

  Scenario: Initialize stock with quantity
    When stock is initialized
    Then a StockInitialized event is raised
    And the on-hand quantity is 100
    And the available quantity is 100

  Scenario: Stock has correct SKU
    When stock is initialized
    Then the SKU is "TSHIRT-BLK-M"

  Scenario: Stock has correct reorder settings
    When stock is initialized
    Then the reorder point is 10
    And the reorder quantity is 50
