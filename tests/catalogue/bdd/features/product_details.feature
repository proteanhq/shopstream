Feature: Product details management
  Product metadata can be updated: title, description, brand, and SEO.

  Background:
    Given a draft product

  Scenario: Update title
    When the product title is updated to "New Title"
    Then the product title is "New Title"
    And a ProductDetailsUpdated product event is raised

  Scenario: Update description
    When the product description is updated to "New description text"
    Then the product description is "New description text"

  Scenario: Update brand
    When the product brand is updated to "Adidas"
    Then the product brand is "Adidas"

  Scenario: Update attributes
    When the product attributes are updated to '{"color": "red", "size": "XL"}'
    Then the product has attributes

  Scenario: Update SEO metadata
    When the product SEO is updated with slug "running-shoes"
    Then the product SEO slug is "running-shoes"

  Scenario: Partial update only changes specified fields
    When the product title is updated to "Updated Title"
    Then the product description is "A test product description"
