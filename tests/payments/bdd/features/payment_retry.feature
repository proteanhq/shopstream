Feature: Payment retry
  Failed payments can be retried up to the maximum attempt limit.

  Scenario: Retry a failed payment
    Given a new payment is initiated
    And the payment has failed
    When the payment is retried
    Then the payment status is "Pending"
    And the attempt count is 2

  Scenario: Cannot retry after max attempts
    Given a new payment is initiated
    And the payment has exhausted all retries
    Then retrying the payment fails with a validation error
