Feature: Redemption lifecycle
  A redemption moves through reserve → issue → complete, or compensates when the
  voucher cannot be issued. (The RedemptionSaga orchestrates these transitions at runtime.)

  Scenario: Request a redemption
    When a redemption is requested for 100 points
    Then the redemption status is "requested"
    And a RedemptionRequested event is raised

  Scenario: Reserve points then issue a voucher
    Given a requested redemption
    When points are reserved
    And a voucher "VCHR-1" is issued
    Then the redemption status is "voucher_issued"

  Scenario: Complete a redemption
    Given a requested redemption
    When points are reserved
    And a voucher "VCHR-1" is issued
    And the redemption is completed
    Then the redemption status is "completed"
    And a RedemptionCompleted event is raised

  Scenario: Compensate a failed voucher
    Given a requested redemption
    When points are reserved
    And voucher issuance fails with reason "sold out"
    And the redemption is compensated for 100 points
    Then the redemption status is "compensated"
    And a RedemptionCompensated event is raised

  Scenario: A failing reward code cannot issue a voucher
    When a voucher code is requested for reward "FAIL-STOCK"
    Then voucher issuance is unavailable

  Scenario: A normal reward code issues a voucher code
    When a voucher code is requested for reward "GIFT10"
    Then a voucher code is returned
