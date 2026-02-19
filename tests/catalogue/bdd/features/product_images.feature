Feature: Product image management
  Products can have up to 10 images with exactly one primary.

  Scenario: First image becomes primary automatically
    Given a draft product
    When an image is added with URL "https://example.com/img1.jpg"
    Then the product has 1 image
    And the first image is primary
    And a ProductImageAdded product event is raised

  Scenario: Second image does not become primary
    Given a draft product
    And the product has an image
    When an image is added with URL "https://example.com/img2.jpg"
    Then the product has 2 images
    And the first image is primary

  Scenario: Remove non-primary image
    Given a draft product
    And the product has 2 images
    When the non-primary image is removed
    Then the product has 1 image
    And a ProductImageRemoved product event is raised

  Scenario: Remove primary image promotes next
    Given a draft product
    And the product has 2 images
    When the primary image is removed
    Then the product has 1 image
    And the remaining image is primary

  Scenario: Cannot exceed 10 images
    Given a draft product
    And the product has 10 images
    When an image is added with URL "https://example.com/img11.jpg"
    Then the action fails with a validation error
