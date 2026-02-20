Feature: Invoice lifecycle
  Invoices are generated, issued, and marked paid.

  Scenario: Generate a new invoice
    Given a new invoice is generated
    Then the invoice status is "Draft"
    And the invoice has a number starting with "INV-"

  Scenario: Issue an invoice
    Given a new invoice is generated
    When the invoice is issued
    Then the invoice status is "Issued"

  Scenario: Mark invoice as paid
    Given a new invoice is generated
    And the invoice was issued
    When the invoice is marked as paid
    Then the invoice status is "Paid"

  Scenario: Void a draft invoice
    Given a new invoice is generated
    When the invoice is voided with reason "Order cancelled"
    Then the invoice status is "Voided"
