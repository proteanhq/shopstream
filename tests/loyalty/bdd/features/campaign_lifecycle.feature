Feature: Promo campaign lifecycle
  Promotional campaigns are event-sourced and move through a small state machine:
  draft → active ↔ paused, and any state → expired.

  Scenario: Launch a campaign
    When a campaign is launched
    Then the campaign status is "draft"
    And a CampaignLaunched event is raised

  Scenario: Activate a draft campaign
    Given a draft promo campaign
    When the campaign is activated
    Then the campaign status is "active"
    And a CampaignActivated event is raised

  Scenario: Pause an active campaign
    Given a draft promo campaign
    When the campaign is activated
    And the campaign is paused
    Then the campaign status is "paused"

  Scenario: Cannot pause a draft campaign
    Given a draft promo campaign
    When the campaign is paused
    Then the action fails with a validation error

  Scenario: Expire a campaign
    Given a draft promo campaign
    When the campaign is expired
    Then the campaign status is "expired"
