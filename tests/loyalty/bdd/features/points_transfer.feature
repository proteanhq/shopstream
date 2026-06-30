Feature: Points transfer between reward accounts
  Points can be moved between two accounts via the TransferPoints domain service,
  which conserves the total and refuses invalid transfers.

  Scenario: Transfer conserves the total
    Given a source account with 100 points and a target account with 0 points
    When 40 points are transferred from source to target
    Then the source balance is 60
    And the target balance is 40

  Scenario: Cannot transfer more than the source balance
    Given a source account with 30 points and a target account with 0 points
    When 50 points are transferred from source to target
    Then the transfer fails with a validation error

  Scenario: Cannot transfer a non-positive amount
    Given a source account with 100 points and a target account with 0 points
    When 0 points are transferred from source to target
    Then the transfer fails with a validation error

  Scenario: Cannot transfer to a closed account
    Given a source account with 100 points and a closed target account
    When 10 points are transferred from source to target
    Then the transfer fails with a validation error
