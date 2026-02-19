Feature: Customer Profile Management
  Customers can update their profile information including name, phone, and date of birth.
  Profile updates use partial update semantics — only provided fields change.

  Background:
    Given a registered customer

  Scenario: Update first name only
    When the customer updates their profile with first name "Jane"
    Then the customer profile first name is "Jane"
    And the customer profile last name is "User"
    And a ProfileUpdated event is raised

  Scenario: Update last name only
    When the customer updates their profile with last name "Doe"
    Then the customer profile last name is "Doe"
    And the customer profile first name is "Test"
    And a ProfileUpdated event is raised

  Scenario: Update phone number
    When the customer updates their profile with phone "+1-555-987-6543"
    Then the customer profile phone number is "+1-555-987-6543"
    And a ProfileUpdated event is raised

  Scenario: Update date of birth
    When the customer updates their profile with date of birth "1990-05-15"
    Then the customer profile date of birth is "1990-05-15"
    And a ProfileUpdated event is raised

  Scenario: Update first and last name together
    When the customer updates their profile with name "Alice" "Wonder"
    Then the customer profile first name is "Alice"
    And the customer profile last name is "Wonder"
    And a ProfileUpdated event is raised

  Scenario: Clear phone number
    Given the customer has phone number "+1-555-000-0000"
    When the customer updates their profile with no phone
    Then the customer has no phone number
    And a ProfileUpdated event is raised
