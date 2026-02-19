Feature: Product creation
  Products are created in Draft status with a unique SKU.

  Scenario: Create a product with required fields
    When a product is created with SKU "SHOE-001" and title "Running Shoes"
    Then the product status is "Draft"
    And a ProductCreated product event is raised

  Scenario: Product has default Public visibility
    When a product is created with SKU "SHOE-001" and title "Running Shoes"
    Then the product visibility is "Public"

  Scenario: Product starts with no variants
    When a product is created with SKU "SHOE-001" and title "Running Shoes"
    Then the product has 0 variants

  Scenario: Product starts with no images
    When a product is created with SKU "SHOE-001" and title "Running Shoes"
    Then the product has 0 images

  Scenario: Create a product with full details
    When a product is created with SKU "SHOE-001" title "Running Shoes" seller "seller-1" category "cat-001" brand "Nike"
    Then the product title is "Running Shoes"
    And the product brand is "Nike"
    And a ProductCreated product event is raised

  Scenario: Product has timestamps
    When a product is created with SKU "SHOE-001" and title "Running Shoes"
    Then the product has a created_at timestamp
    And the product has an updated_at timestamp
