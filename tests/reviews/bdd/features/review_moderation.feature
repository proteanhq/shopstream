Feature: Review moderation
  Moderators can approve or reject pending reviews.

  Scenario: Approve a pending review
    Given a pending review
    When the review is approved by moderator "mod-001"
    Then the review status is "Published"
    And a ReviewApproved event is raised

  Scenario: Reject a pending review
    Given a pending review
    When the review is rejected by moderator "mod-001" with reason "Spam content"
    Then the review status is "Rejected"
    And a ReviewRejected event is raised

  Scenario: Cannot approve an already published review
    Given a published review
    When the review is approved by moderator "mod-002"
    Then the review action fails with a validation error
