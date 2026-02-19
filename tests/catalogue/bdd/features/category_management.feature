Feature: Category management
  Categories organize products in a hierarchy up to 5 levels deep.

  Scenario: Create a top-level category
    When a category is created with name "Electronics"
    Then the category name is "Electronics"
    And the category level is 0
    And the category is active
    And a CategoryCreated category event is raised

  Scenario: Create a subcategory
    When a category is created with name "Smartphones" under parent "parent-001" at level 1
    Then the category name is "Smartphones"
    And the category level is 1

  Scenario: Update category name
    Given an active category
    When the category name is updated to "Consumer Electronics"
    Then the category name is "Consumer Electronics"
    And a CategoryDetailsUpdated category event is raised

  Scenario: Update category attributes
    Given an active category
    When the category attributes are updated to '{"icon": "laptop"}'
    Then the category has attributes

  Scenario: Reorder category
    Given an active category
    When the category display order is changed to 5
    Then the category display order is 5
    And a CategoryReordered category event is raised

  Scenario: Deactivate category
    Given an active category
    When the category is deactivated
    Then the category is inactive
    And a CategoryDeactivated category event is raised

  Scenario: Cannot deactivate already inactive category
    Given an inactive category
    When the category is deactivated
    Then the action fails with a validation error
