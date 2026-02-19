Feature: Product lifecycle
  Products follow a forward-only state machine: Draft -> Active -> Discontinued -> Archived.

  Scenario: Activate a draft product with variants
    Given a draft product with a variant
    When the product is activated
    Then the product status is "Active"
    And a ProductActivated product event is raised

  Scenario: Cannot activate without variants
    Given a draft product
    When the product is activated
    Then the action fails with a validation error

  Scenario: Cannot activate an already active product
    Given an active product
    When the product is activated
    Then the action fails with a validation error

  Scenario: Discontinue an active product
    Given an active product
    When the product is discontinued
    Then the product status is "Discontinued"
    And a ProductDiscontinued product event is raised

  Scenario: Cannot discontinue a draft product
    Given a draft product
    When the product is discontinued
    Then the action fails with a validation error

  Scenario: Archive a discontinued product
    Given a discontinued product
    When the product is archived
    Then the product status is "Archived"
    And a ProductArchived product event is raised

  Scenario: Cannot archive an active product
    Given an active product
    When the product is archived
    Then the action fails with a validation error

  Scenario: Cannot archive a draft product
    Given a draft product
    When the product is archived
    Then the action fails with a validation error
