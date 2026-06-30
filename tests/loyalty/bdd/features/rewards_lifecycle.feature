Feature: Reward account lifecycle
  Customers enrol in the rewards program, earn and redeem points, progress through
  tiers, and can have their account closed.

  Scenario: Enrol a new customer
    When a customer enrols in the rewards program
    Then the account status is "Active"
    And the account tier is "bronze"
    And a RewardAccountEnrolled event is raised

  Scenario: Earn points
    Given an enrolled reward account
    When the account earns 120 points
    Then the points balance is 120
    And the lifetime points is 120
    And a PointsEarned event is raised

  Scenario: Redeem points lowers balance but not lifetime
    Given an enrolled reward account with 200 points
    When the account redeems 50 points
    Then the points balance is 150
    And the lifetime points is 200
    And a PointsRedeemed event is raised

  Scenario: Cannot redeem more than the balance
    Given an enrolled reward account with 30 points
    When the account redeems 50 points
    Then the action fails with a validation error

  Scenario: Earning past a threshold upgrades the tier
    Given an enrolled reward account
    When the account earns 1500 points
    Then the account tier is "silver"
    And a TierUpgraded event is raised

  Scenario: A single large earn can jump multiple tiers
    Given an enrolled reward account
    When the account earns 6000 points
    Then the account tier is "gold"

  Scenario: Closing an account
    Given an enrolled reward account
    When the account is closed
    Then the account status is "Closed"
    And a RewardAccountClosed event is raised
