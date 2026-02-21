Feature: Review voting
  Customers can vote on reviews as helpful or unhelpful.

  Scenario: Vote helpful on a review
    Given a pending review
    When customer "cust-voter" votes "Helpful" on the review
    Then the review helpful count is 1

  Scenario: Cannot vote on own review
    Given a pending review by customer "cust-owner"
    When customer "cust-owner" votes "Helpful" on the review
    Then the review action fails with a validation error

  Scenario: Cannot vote twice on same review
    Given a pending review
    And customer "cust-dupe" has voted "Helpful"
    When customer "cust-dupe" votes "Unhelpful" on the review
    Then the review action fails with a validation error
