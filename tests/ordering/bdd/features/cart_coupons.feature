Feature: Cart coupon management
  Coupons can be applied to active carts.

  Scenario: Apply coupon to cart
    Given an active cart
    When a coupon "SAVE10" is applied to the cart
    Then a CartCouponApplied cart event is raised

  Scenario: Cannot apply same coupon twice
    Given an active cart
    And the cart has a coupon applied
    When a coupon "SAVE10" is applied to the cart
    Then the cart action fails with a validation error

  Scenario: Cannot apply coupon to converted cart
    Given an active cart
    And the cart has an item
    And the cart is converted
    When a coupon "SAVE10" is applied to the cart
    Then the cart action fails with a validation error

  Scenario: Cannot apply coupon to abandoned cart
    Given an active cart
    And the cart is abandoned
    When a coupon "SAVE10" is applied to the cart
    Then the cart action fails with a validation error
