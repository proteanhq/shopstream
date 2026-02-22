Feature: Preference management
  Customers can manage their notification channel preferences and unsubscribe from specific types.

  Scenario: Default preferences created for new customer
    Given a new customer "cust-pref-bdd-1"
    When default preferences are created
    Then email is enabled
    And SMS is disabled
    And push is disabled

  Scenario: Customer enables SMS notifications
    Given a customer with default preferences
    When the customer enables SMS
    Then SMS is enabled

  Scenario: Customer sets quiet hours
    Given a customer with default preferences
    When the customer sets quiet hours from "22:00" to "08:00"
    Then quiet hours are set to "22:00" - "08:00"

  Scenario: Customer unsubscribes from a notification type
    Given a customer with default preferences
    When the customer unsubscribes from "CartRecovery"
    Then the customer is not subscribed to "CartRecovery"
