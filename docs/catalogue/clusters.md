## Cluster: Category

```mermaid
classDiagram
    class catalogue_category_category_Category {
        <<Aggregate>>
        +attributes Dict
        +created_at DateTime
        +display_order Integer
        +id "Auto (identifier)"
        +is_active Boolean
        +level Integer
        +name "String (required)"
        +parent_category_id Identifier
        +updated_at DateTime
    }
```

## Cluster: Product

```mermaid
classDiagram
    class catalogue_product_product_Product {
        <<Aggregate>>
        +attributes Dict
        +brand String
        +category_id Identifier
        +created_at DateTime
        +description Text
        +id "Auto (identifier)"
        +images "Image[]"
        +seller_id Identifier
        +seo SEO
        +sku "SKU (required)"
        +status Status
        +title "String (required)"
        +updated_at DateTime
        +variants "Variant[]"
        +visibility String
    }
    note for catalogue_product_product_Product "exactly_one_primary_image_when_images_exist, images_cannot_exceed_maximum"
    class catalogue_product_product_Image {
        <<Entity>>
        +alt_text String
        +display_order Integer
        +id "Auto (identifier)"
        +is_primary Boolean
        +product Product
        +url "String (required)"
    }
    catalogue_product_product_Product "1" o-- "*" catalogue_product_product_Image : Image
    class catalogue_product_product_Variant {
        <<Entity>>
        +attributes Dict
        +dimensions Dimensions
        +id "Auto (identifier)"
        +is_active Boolean
        +price "Price (required)"
        +product Product
        +variant_sku "SKU (required)"
        +weight Weight
    }
    catalogue_product_product_Product "1" o-- "*" catalogue_product_product_Variant : Variant
    class catalogue_product_product_Dimensions {
        <<ValueObject>>
        +height Float
        +length Float
        +unit String
        +width Float
    }
    note for catalogue_product_product_Dimensions "unit_must_be_valid"
    class catalogue_product_product_Price {
        <<ValueObject>>
        +base_price "Float (required)"
        +currency String
        +tier_prices Dict
    }
    note for catalogue_product_product_Price "tier_prices_must_be_valid"
    class catalogue_product_product_SEO {
        <<ValueObject>>
        +meta_description String
        +meta_title String
        +slug String
    }
    note for catalogue_product_product_SEO "slug_must_be_url_safe"
    catalogue_product_product_Product *-- catalogue_product_product_SEO : SEO
    class catalogue_product_product_Weight {
        <<ValueObject>>
        +unit String
        +value Float
    }
    note for catalogue_product_product_Weight "unit_must_be_valid"
    class catalogue_shared_sku_SKU {
        <<ValueObject>>
        +code "String (required)"
    }
    note for catalogue_shared_sku_SKU "code_must_be_valid_format"
    catalogue_product_product_Product *-- catalogue_shared_sku_SKU : SKU
```
