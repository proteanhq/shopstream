Feature: Review submission
  Customers can submit product reviews with ratings and content.

  Scenario: Submit a basic review
    When a customer submits a review for product "prod-001" with rating 4
    Then the review status is "Pending"
    And a ReviewSubmitted event is raised

  Scenario: Submit a review with images
    When a customer submits a review with 3 images
    Then the review has 3 images

  Scenario: Submit a review with pros and cons
    When a customer submits a review with pros and cons
    Then the review has pros and cons

  Scenario: Cannot submit with short body
    When a customer submits a review with body "Too short"
    Then the review action fails with a validation error
