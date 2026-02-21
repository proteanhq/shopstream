Feature: Review lifecycle
  Reviews transition through states: Pending -> Published -> Removed.

  Scenario: Full review lifecycle - submit, approve, remove
    When a customer submits a review for product "prod-lc" with rating 5
    And the review is approved by moderator "mod-001"
    And the review is removed by "Admin" for reason "Policy violation"
    Then the review status is "Removed"

  Scenario: Rejected review can be edited and resubmitted
    Given a pending review
    When the review is rejected by moderator "mod-001" with reason "Needs improvement"
    And the review body is edited to "Completely rewritten content that is long enough to pass validation."
    Then the review status is "Pending"
    And the review is marked as edited

  Scenario: Seller reply on published review
    Given a published review
    When seller "seller-001" replies with "Thank you for the review!"
    Then the review has a seller reply
    And a SellerReplyAdded event is raised
