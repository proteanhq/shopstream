## Cluster: DefaultOutbox

```mermaid
classDiagram
    class abc_DefaultOutbox {
        <<Aggregate>>
        +causation_id String
        +correlation_id String
        +created_at DateTime
        +data "Dict (required)"
        +id "Auto (identifier)"
        +last_error Dict
        +last_processed_at DateTime
        +locked_by String
        +locked_until DateTime
        +max_retries Integer
        +message_id "String (required)"
        +metadata_ "String (required)"
        +next_retry_at DateTime
        +priority Integer
        +published_at DateTime
        +retry_count Integer
        +sequence_number Integer
        +status String
        +stream_name "String (required)"
        +target_broker String
        +type "String (required)"
    }
```

## Cluster: MemoryOutbox

```mermaid
classDiagram
    class abc_MemoryOutbox {
        <<Aggregate>>
        +causation_id String
        +correlation_id String
        +created_at DateTime
        +data "Dict (required)"
        +id "Auto (identifier)"
        +last_error Dict
        +last_processed_at DateTime
        +locked_by String
        +locked_until DateTime
        +max_retries Integer
        +message_id "String (required)"
        +metadata_ "String (required)"
        +next_retry_at DateTime
        +priority Integer
        +published_at DateTime
        +retry_count Integer
        +sequence_number Integer
        +status String
        +stream_name "String (required)"
        +target_broker String
        +type "String (required)"
    }
```

## Cluster: ShoppingCart

```mermaid
classDiagram
    class ordering_cart_cart_ShoppingCart {
        <<Aggregate>>
        +applied_coupons "List[String]"
        +created_at DateTime
        +customer_id Identifier
        +id "Auto (identifier)"
        +items "CartItem[]"
        +session_id String
        +status Status
        +updated_at DateTime
    }
    note for ordering_cart_cart_ShoppingCart cart_must_have_items_to_convert
    class ordering_cart_cart_CartItem {
        <<Entity>>
        +added_at DateTime
        +id "Auto (identifier)"
        +product_id "Identifier (required)"
        +quantity "Integer (required)"
        +shopping_cart ShoppingCart
        +variant_id "Identifier (required)"
    }
    ordering_cart_cart_ShoppingCart "1" o-- "*" ordering_cart_cart_CartItem : CartItem
```

## Cluster: Order

```mermaid
classDiagram
    class ordering_order_order_Order {
        <<Aggregate, EventSourced>>
        +billing_address ShippingAddress
        +cancellation_reason String
        +cancelled_by String
        +carrier String
        +coupon_code String
        +created_at DateTime
        +customer_id "Identifier (required)"
        +estimated_delivery String
        +id "Auto (identifier)"
        +items "OrderItem[]"
        +payment_id String
        +payment_method String
        +payment_status String
        +pricing OrderPricing
        +shipment_id String
        +shipping_address ShippingAddress
        +status Status
        +tracking_number String
        +updated_at DateTime
    }
    class ordering_order_order_OrderItem {
        <<Entity>>
        +discount Float
        +id "Auto (identifier)"
        +item_status Status
        +order Order
        +product_id "Identifier (required)"
        +quantity "Integer (required)"
        +sku "String (required)"
        +tax_amount Float
        +title "String (required)"
        +unit_price "Float (required)"
        +variant_id "Identifier (required)"
    }
    ordering_order_order_Order "1" o-- "*" ordering_order_order_OrderItem : OrderItem
    class ordering_order_order_OrderPricing {
        <<ValueObject>>
        +currency String
        +discount_total Float
        +grand_total Float
        +shipping_cost Float
        +subtotal Float
        +tax_total Float
    }
    ordering_order_order_Order *-- ordering_order_order_OrderPricing : OrderPricing
    class ordering_order_order_ShippingAddress {
        <<ValueObject>>
        +city "String (required)"
        +country "String (required)"
        +postal_code "String (required)"
        +state String
        +street "String (required)"
    }
    ordering_order_order_Order *-- ordering_order_order_ShippingAddress : ShippingAddress
    ordering_order_order_Order *-- ordering_order_order_ShippingAddress : ShippingAddress
```
