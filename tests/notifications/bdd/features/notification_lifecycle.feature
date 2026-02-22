Feature: Notification lifecycle
  Notifications transition through states: Pending -> Sent -> Delivered, or Pending -> Failed -> (retry) -> Pending.

  Scenario: Notification is created in Pending status
    Given a new notification for customer "cust-bdd-1"
    Then the notification status is "Pending"
    And a NotificationCreated event is raised

  Scenario: Notification can be marked as sent
    Given a pending notification
    When the notification is marked as sent
    Then the notification status is "Sent"
    And a NotificationSent event is raised

  Scenario: Sent notification can be delivered
    Given a sent notification
    When the notification is marked as delivered
    Then the notification status is "Delivered"

  Scenario: Pending notification can be cancelled
    Given a pending notification
    When the notification is cancelled with reason "Customer opted out"
    Then the notification status is "Cancelled"
    And a NotificationCancelled event is raised

  Scenario: Failed notification can be retried
    Given a failed notification
    When the notification is retried
    Then the notification status is "Pending"
    And a NotificationRetried event is raised
