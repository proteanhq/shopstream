Feature: Customer Account Lifecycle
  Customer accounts transition through Active, Suspended, and Closed states.

  Background:
    Given a registered customer

  Scenario: Suspend an active account
    When the account is suspended with reason "Fraud investigation"
    Then the customer status is "Suspended"
    And an AccountSuspended event is raised with reason "Fraud investigation"

  Scenario: Reactivate a suspended account
    Given the account is suspended
    When the account is reactivated
    Then the customer status is "Active"
    And an AccountReactivated event is raised

  Scenario: Close an active account
    When the account is closed
    Then the customer status is "Closed"
    And an AccountClosed event is raised

  Scenario: Close a suspended account
    Given the account is suspended
    When the account is closed
    Then the customer status is "Closed"
    And an AccountClosed event is raised

  Scenario: Cannot suspend an already suspended account
    Given the account is suspended
    When the account is suspended with reason "Another reason"
    Then the action fails with a validation error

  Scenario: Cannot suspend a closed account
    Given the account is closed
    When the account is suspended with reason "Too late"
    Then the action fails with a validation error

  Scenario: Cannot reactivate an active account
    When the account is reactivated
    Then the action fails with a validation error

  Scenario: Cannot reactivate a closed account
    Given the account is closed
    When the account is reactivated
    Then the action fails with a validation error

  Scenario: Cannot close an already closed account
    Given the account is closed
    When the account is closed
    Then the action fails with a validation error
