Feature: Customer Registration
  Customers register with an external ID and email address.
  Registration creates an active customer and raises a registration event.

  Scenario: Successful registration with minimal data
    When a customer registers with external ID "EXT-001" and email "alice@example.com"
    Then the customer status is "Active"
    And the customer tier is "Standard"
    And a CustomerRegistered event is raised

  Scenario: Registration with full profile
    When a customer registers with external ID "EXT-002" email "bob@example.com" name "Bob" "Smith"
    Then the customer profile first name is "Bob"
    And the customer profile last name is "Smith"
    And a CustomerRegistered event is raised

  Scenario: Registration with phone number
    When a customer registers with external ID "EXT-003" email "carol@example.com" name "Carol" "Jones" and phone "+1-555-123-4567"
    Then the customer profile phone number is "+1-555-123-4567"

  Scenario: Registration sets timestamps
    When a customer registers with external ID "EXT-004" and email "dave@example.com"
    Then the customer has a registered_at timestamp
    And the customer has no last_login_at timestamp

  Scenario: Registration event contains correct data
    When a customer registers with external ID "EXT-005" email "eve@example.com" name "Eve" "Wilson"
    Then the CustomerRegistered event contains external_id "EXT-005"
    And the CustomerRegistered event contains email "eve@example.com"
    And the CustomerRegistered event contains first_name "Eve"

  Scenario: Registration with invalid email fails
    When a customer registers with external ID "EXT-006" and email "not-an-email"
    Then the registration fails with a validation error
