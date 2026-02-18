# Ubiquitous Language Glossary

> The shared vocabulary of ShopStream. These terms mean the same thing
> in conversation, in requirements, and in code. When a domain expert
> says "order," a developer reads `Order`, and a test asserts on
> `OrderStatus` -- they all mean the same thing.

---

## Identity Context

### Customer

A person who has registered with the platform. Identified by a system-assigned ID
and an `external_id` from the registration source (e.g., an OAuth provider or legacy
system). A Customer is the root of everything identity-related: profile, addresses,
account status, and loyalty tier.

Not to be confused with "user" (a system/auth concept) or "shopper" (an Ordering concept).

&rarr; [`Customer`](../src/identity/customer/customer.py) (Aggregate)

### Profile

The personal information associated with a Customer -- first name, last name, phone
number, and date of birth. A Profile has no identity of its own; it exists only as
part of a Customer. Changing any profile field replaces the entire Profile (immutability).

&rarr; [`Profile`](../src/identity/customer/customer.py) (Value Object)

### Address

A physical location associated with a Customer -- street, city, state, postal code,
country. Each Address has its own identity (it can be added, updated, or removed
independently) and a label (Home, Work, Other). A Customer can have up to 10 addresses,
and exactly one must be marked as default when any exist.

&rarr; [`Address`](../src/identity/customer/customer.py) (Entity)

### Email Address

A validated email address. The email format is enforced at construction time through
invariant validation -- no whitespace, exactly one `@`, valid local and domain parts.

&rarr; [`EmailAddress`](../src/identity/shared/email.py) (Value Object)

### Phone Number

A validated phone number that accepts digits, spaces, hyphens, parentheses, and an
optional leading `+`. Must contain at least one digit.

&rarr; [`PhoneNumber`](../src/identity/shared/phone.py) (Value Object)

### Geo Coordinates

A latitude/longitude pair for address geolocation. Both coordinates are required when
provided (you cannot have latitude without longitude or vice versa).

&rarr; [`GeoCoordinates`](../src/identity/customer/customer.py) (Value Object)

### Customer Status

The lifecycle state of a customer account:
- **Active** -- the default state after registration; the account is usable.
- **Suspended** -- the account has been temporarily disabled (requires a reason). Only active accounts can be suspended.
- **Closed** -- the account has been permanently closed. Both active and suspended accounts can be closed.

&rarr; [`CustomerStatus`](../src/identity/customer/customer.py) (Enum)

### Customer Tier

The loyalty level of a customer, progressing upward only:
**Standard** &rarr; **Silver** &rarr; **Gold** &rarr; **Platinum**.
Downgrades are not permitted. Tier affects visibility of tier-restricted products
in the Catalogue context and tier-specific pricing.

&rarr; [`CustomerTier`](../src/identity/customer/customer.py) (Enum)

### Address Label

A classification for an address: **Home**, **Work**, or **Other**. This is a display
hint, not a business rule -- it does not affect how the address is used.

&rarr; [`AddressLabel`](../src/identity/customer/customer.py) (Enum)

---

## Catalogue Context

### Product

A sellable item in the catalogue, identified by a unique SKU. A Product starts as a
Draft, moves to Active when ready for sale (requires at least one variant), can be
Discontinued, and finally Archived. Products belong to a seller and can be categorized.

A Product contains variants (purchasable configurations), images, and SEO metadata.

&rarr; [`Product`](../src/catalogue/product/product.py) (Aggregate)

### Category

A node in the product categorization hierarchy (up to 5 levels deep, 0-4). Categories
organize products for browsing and can have a parent category. Categories can be
reordered and deactivated but not deleted -- deactivation hides them from navigation.

&rarr; [`Category`](../src/catalogue/category/category.py) (Aggregate)

### Variant

A purchasable configuration of a Product -- e.g., a specific size and color combination.
Each Variant has its own SKU, price (with optional tier-specific pricing), and physical
attributes (weight, dimensions). A Variant has identity within its Product.

A Product must have at least one active Variant to be activated.

&rarr; [`Variant`](../src/catalogue/product/product.py) (Entity)

### Image

A product photograph or rendering. Each Image has a URL, alt text, and a display order.
Exactly one image must be marked as primary when any images exist (same pattern as
default addresses in Identity). A Product can have up to 10 images.

&rarr; [`Image`](../src/catalogue/product/product.py) (Entity)

### SKU (Stock Keeping Unit)

A unique identifier code for a product or variant. Format: alphanumeric characters and
hyphens, 3-50 characters, no leading/trailing/consecutive hyphens. Examples:
`ELEC-PHN-001`, `SHOE-RUN-BLK-42`.

&rarr; [`SKU`](../src/catalogue/shared/sku.py) (Value Object)

### Price

The monetary value of a variant, consisting of a base price, currency, and optional
tier-specific prices (a JSON map of tier names to discounted prices). Tier prices must
be less than the base price.

&rarr; [`Price`](../src/catalogue/product/product.py) (Value Object)

### Money

A general-purpose monetary amount with ISO 4217 currency validation. Supports 20
major currencies (USD, EUR, GBP, JPY, etc.).

&rarr; [`Money`](../src/catalogue/shared/money.py) (Value Object)

### SEO Metadata

Search engine optimization data for a product: meta title (max 70 chars), meta
description (max 160 chars), and a URL slug (lowercase alphanumeric + hyphens, no
leading/trailing/consecutive hyphens).

&rarr; [`SEO`](../src/catalogue/product/product.py) (Value Object)

### Dimensions

Physical measurements of a variant: length, width, height in either centimeters (`cm`)
or inches (`in`).

&rarr; [`Dimensions`](../src/catalogue/product/product.py) (Value Object)

### Weight

Physical weight of a variant: a numeric value in kilograms (`kg`), pounds (`lb`),
grams (`g`), or ounces (`oz`).

&rarr; [`Weight`](../src/catalogue/product/product.py) (Value Object)

### Product Status

The lifecycle state of a product:
- **Draft** -- newly created, not yet visible to buyers. Can be edited freely.
- **Active** -- live and purchasable. Requires at least one variant.
- **Discontinued** -- no longer sold, but still visible for reference. Only active products can be discontinued.
- **Archived** -- removed from all visibility. Only discontinued products can be archived.

&rarr; [`ProductStatus`](../src/catalogue/product/product.py) (Enum)

### Product Visibility

Controls who can see a product:
- **Public** -- visible to everyone.
- **Unlisted** -- accessible by direct link but not in search/browse results.
- **Tier Restricted** -- visible only to customers at certain loyalty tiers.

&rarr; [`ProductVisibility`](../src/catalogue/product/product.py) (Enum)

---

## Ordering Context

### Order

A confirmed intent to purchase one or more products, representing a legally meaningful
commitment. An Order captures the complete lifecycle from creation through fulfillment,
payment, shipping, delivery, and potential returns or cancellation.

The Order aggregate uses **event sourcing** -- every state change is captured as an
immutable event, and the current state is reconstructed by replaying those events. This
provides a complete audit trail and enables temporal queries ("what was this order's
status at 3pm yesterday?").

&rarr; [`Order`](../src/ordering/order/order.py) (Aggregate, Event Sourced)

### Shopping Cart

An ephemeral, pre-commitment container for items a customer intends to purchase. Carts
can belong to authenticated customers or anonymous guest sessions. When a guest logs in,
their guest cart can be merged into their authenticated cart.

A cart becomes an Order at checkout (conversion), after which it is no longer modifiable.
Carts that are neither converted nor active for a period are marked as abandoned.

Unlike the Order, the Shopping Cart uses standard CQRS (not event sourced) -- carts are
disposable and don't require the audit trail that orders demand.

&rarr; [`ShoppingCart`](../src/ordering/cart/cart.py) (Aggregate)

### Order Item

A line item within an Order -- a specific product variant at a given quantity and price.
Each Order Item tracks its own lifecycle status (Pending, Reserved, Shipped, Delivered,
Returned) independently, enabling partial shipments and partial returns.

&rarr; [`OrderItem`](../src/ordering/order/order.py) (Entity)

### Cart Item

An item in a shopping cart -- a product variant at a quantity. Unlike Order Items, Cart
Items have no pricing (prices are calculated at checkout time) and no lifecycle status.

&rarr; [`CartItem`](../src/ordering/cart/cart.py) (Entity)

### Shipping Address

The physical destination for order delivery: street, city, state, postal code, country.
Captured as a snapshot at order creation time -- if the customer later changes their
address in the Identity context, this order's shipping address remains unchanged.

&rarr; [`ShippingAddress`](../src/ordering/order/order.py) (Value Object)

### Order Pricing

The financial summary of an order: subtotal (sum of item prices), shipping cost, tax
total, discount total, and grand total. Currency is stored alongside the amounts.
Pricing is recalculated whenever items are added, removed, or quantities change.

&rarr; [`OrderPricing`](../src/ordering/order/order.py) (Value Object)

### Order Status

The 14-state lifecycle of an order, enforced by a state machine with explicitly defined
valid transitions:

| State | Meaning |
|-------|---------|
| **Created** | Order placed, items locked. Can still modify items. |
| **Confirmed** | Customer confirmed, inventory reserved. |
| **Payment Pending** | Payment initiated but not yet captured. |
| **Paid** | Payment successfully captured. |
| **Processing** | Warehouse picking and packing. |
| **Partially Shipped** | Some items shipped, others still processing. |
| **Shipped** | All items handed to carrier. |
| **Delivered** | Customer received the package. |
| **Completed** | Return window expired, order finalized. (Terminal) |
| **Return Requested** | Customer requested a return after delivery. |
| **Return Approved** | Return request approved by admin/system. |
| **Returned** | Returned items received at warehouse. |
| **Cancelled** | Order cancelled before shipping. |
| **Refunded** | Money returned to customer. (Terminal) |

&rarr; [`OrderStatus`](../src/ordering/order/order.py) (Enum)

### Item Status

The lifecycle of an individual order item within a shipment:
**Pending** &rarr; **Reserved** &rarr; **Shipped** &rarr; **Delivered** &rarr; **Returned**.

&rarr; [`ItemStatus`](../src/ordering/order/order.py) (Enum)

### Cart Status

The lifecycle of a shopping cart:
- **Active** -- items can be added, removed, updated.
- **Converted** -- cart has been checked out and an Order was created from it.
- **Abandoned** -- cart was not checked out within the abandonment window.

&rarr; [`CartStatus`](../src/ordering/cart/cart.py) (Enum)

### Cancellation Actor

Who initiated an order cancellation: **Customer** (self-service), **System** (automated
rule, e.g., payment timeout), or **Admin** (manual intervention).

&rarr; [`CancellationActor`](../src/ordering/order/order.py) (Enum)

---

## Cross-Context Terms

### customer_id

An opaque identifier that the Ordering context uses to reference a Customer in the
Identity context. The Ordering context never loads or inspects the Customer aggregate --
it only stores the ID. This is the anti-corruption boundary between contexts.

### product_id / variant_id

Opaque identifiers that the Ordering context uses to reference Products and Variants
from the Catalogue context. Order Items store these IDs along with a snapshot of the
SKU, title, and price at the time of order creation. If the product's price or title
changes later, existing orders are unaffected.

### seller_id

An identifier referencing the seller/merchant who owns a Product. The seller concept
is not modeled as a full aggregate in ShopStream (it would belong to a Merchant or
Marketplace context in a larger system), so it appears only as a reference ID.

### category_id

An identifier linking a Product to its Category. Products reference categories by ID
rather than embedding category data, because categories can change independently of
products.
