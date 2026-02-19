Feature: Customer Address Management
  Customers can manage up to 10 addresses with exactly one default.

  Background:
    Given a registered customer

  Scenario: Add first address becomes default
    When the customer adds an address "123 Main St" "Springfield" "62701" "US"
    Then the customer has 1 address
    And the address is the default
    And an AddressAdded event is raised

  Scenario: Add second address does not change default
    Given the customer has a default address
    When the customer adds an address "456 Oak Ave" "Chicago" "60601" "US"
    Then the customer has 2 addresses
    And the first address is still the default

  Scenario: Add address with label
    When the customer adds an address "789 Office Rd" "New York" "10001" "US" with label "Work"
    Then the customer has 1 address
    And the address label is "Work"

  Scenario: Update address street
    Given the customer has a default address
    When the customer updates the address street to "999 New Street"
    Then the address street is "999 New Street"
    And an AddressUpdated event is raised

  Scenario: Remove non-default address
    Given the customer has 2 addresses
    When the non-default address is removed
    Then the customer has 1 address
    And an AddressRemoved event is raised

  Scenario: Remove default address reassigns default
    Given the customer has 2 addresses
    When the default address is removed
    Then the customer has 1 address
    And the remaining address is the default
    And an AddressRemoved event is raised

  Scenario: Cannot remove last address
    Given the customer has a default address
    When the last address is removed
    Then the action fails with a validation error

  Scenario: Set a different default address
    Given the customer has 2 addresses
    When the second address is set as default
    Then the second address is the default
    And the first address is no longer default
    And a DefaultAddressChanged event is raised

  Scenario: Cannot exceed 10 addresses
    Given the customer has 10 addresses
    When the customer adds an address "11th St" "Town" "00000" "US"
    Then the action fails with a validation error
