# ShopStream Domain Documentation

> The analysis model behind ShopStream -- domain knowledge, ubiquitous language,
> business scenarios, and design rationale that drove the architecture.

## Why This Exists

ShopStream is built with Domain-Driven Design using the [Protean](https://github.com/proteanhq/protean) framework.
The code expresses *what* was built. This documentation explains *why* -- the domain
knowledge, business rules, and design decisions that shaped the implementation.

If you're learning DDD with Protean, start here to understand the domain before
diving into the code. If you're an experienced developer, use this as a reference
for how real-world e-commerce concepts map to DDD building blocks.

## How to Read This

### Start with the Big Picture

1. **[Context Map](context-map.md)** -- How the four bounded contexts relate to each
   other. Understand the overall architecture and what each context owns.

2. **[Glossary](glossary.md)** -- The ubiquitous language of ShopStream. Every term
   means the same thing in conversation, in requirements, and in code.

### Then Pick a Domain

Each bounded context has a **narrative** (the business story) and **scenarios**
(step-by-step traces through the code):

| Context | Narrative | Key Scenarios |
|---------|-----------|--------------|
| **[Identity](identity/)** | [Domain narrative](identity/README.md) | [Customer Registration](identity/scenarios/customer-registration.md) |
| **[Catalogue](catalogue/)** | [Domain narrative](catalogue/README.md) | [Product Lifecycle](catalogue/scenarios/product-lifecycle.md) |
| **[Ordering](ordering/)** | [Domain narrative](ordering/README.md) | [Cart Checkout](ordering/scenarios/cart-to-order.md), [Order Fulfillment](ordering/scenarios/order-fulfillment.md) |
| **[Inventory](inventory/)** | [Domain narrative](inventory/README.md) | [Stock Receiving](inventory/scenarios/stock-receiving.md), [Reservation Lifecycle](inventory/scenarios/reservation-lifecycle.md) |

### Recommended Reading Order

**For newcomers to DDD:**
1. Context Map (understand the boundaries)
2. Identity narrative (simplest domain, one aggregate)
3. Customer Registration scenario (trace one command end-to-end)
4. Catalogue narrative (two aggregates, product lifecycle)
5. Ordering narrative (event sourcing, 14-state machine)
6. Cart Checkout scenario (cross-aggregate operation)
7. Inventory narrative (event sourcing for audit trail, reservation pattern)
8. Reservation Lifecycle scenario (reserve/confirm/commit flow)

**For experienced DDD practitioners:**
1. Ordering narrative (event sourcing + CQRS in same BC, design decisions)
2. Order Fulfillment scenario (state machine + event replay in detail)
3. Inventory narrative (stock level model, reservation with expiry, notification events)
4. Glossary (see how UL maps to code elements)

## Document Structure

```
docs/
├── README.md              ← You are here
├── context-map.md         ← Bounded context relationships
├── glossary.md            ← Ubiquitous Language (all terms)
├── identity/
│   ├── README.md          ← Business context, domain model, events, commands
│   └── scenarios/
│       └── customer-registration.md
├── catalogue/
│   ├── README.md
│   └── scenarios/
│       └── product-lifecycle.md
├── ordering/
│   ├── README.md
│   └── scenarios/
│       ├── cart-to-order.md
│       └── order-fulfillment.md
└── inventory/
    ├── README.md
    └── scenarios/
        ├── stock-receiving.md
        └── reservation-lifecycle.md
```

## Domain at a Glance

| | Identity | Catalogue | Ordering | Inventory |
|---|---------|-----------|----------|-----------|
| **Aggregates** | Customer | Product, Category | Order (ES), ShoppingCart | InventoryItem (ES), Warehouse |
| **Entities** | Address | Variant, Image | OrderItem, CartItem | Reservation, Zone |
| **Value Objects** | Profile, EmailAddress, PhoneNumber, GeoCoordinates | SKU, Price, SEO, Dimensions, Weight, Money | ShippingAddress, OrderPricing | StockLevels, WarehouseAddress |
| **Events** | 10 | 13 | 25 | 18 |
| **Commands** | 10 | 14 | 27 | 16 |
| **Projections** | 4 | 5 | 6 | 6 |
| **API Endpoints** | 10 | 14 | 25 | 16 |
| **Persistence** | CQRS | CQRS | Event Sourced (Order) + CQRS (Cart) | Event Sourced (InventoryItem) + CQRS (Warehouse) |

## Conventions in This Documentation

- **Domain narratives** explain the *business context* and *design rationale* --
  why things are the way they are.
- **Scenario walkthroughs** trace a *specific business operation* from API request
  through command, aggregate, event, and projection -- with links to source code.
- **The glossary** defines every term in the ubiquitous language, linked to the
  code element that implements it.
- Source code links use relative paths (e.g., `../../src/identity/customer/customer.py`)
  and work when browsing on GitHub.
- Mermaid diagrams render natively on GitHub.

## Future: Living Documentation

This documentation will evolve:

- **Auto-generated domain maps** -- A Protean introspection script will extract
  aggregate diagrams, field tables, event catalogs, and state machine diagrams
  directly from the code's registry. Humans write the narratives; machines extract
  the structure.
- **Docstring-as-glossary** -- The glossary will be auto-generated from docstrings
  on domain elements, keeping definitions in sync with code.
- **CI freshness checks** -- Auto-generated docs will be validated against live code
  on every PR, ensuring documentation never goes stale.
