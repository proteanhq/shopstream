# Event & Command Catalog

## Category (`catalogue.category.category.Category`)

### Events

#### CategoryCreated

- **Type**: `Catalogue.CategoryCreated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| category_id | Identifier | Yes | min_length=1 |
| level | Integer | Yes | — |
| name | String | Yes | max_length=255, min_length=1 |
| parent_category_id | Identifier | No | — |

#### CategoryDeactivated

- **Type**: `Catalogue.CategoryDeactivated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| category_id | Identifier | Yes | min_length=1 |
| deactivated_at | DateTime | Yes | — |

#### CategoryDetailsUpdated

- **Type**: `Catalogue.CategoryDetailsUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attributes | Dict | No | — |
| category_id | Identifier | Yes | min_length=1 |
| name | String | Yes | max_length=255, min_length=1 |

#### CategoryReordered

- **Type**: `Catalogue.CategoryReordered.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| category_id | Identifier | Yes | min_length=1 |
| new_order | Integer | Yes | — |
| previous_order | Integer | Yes | — |

### Commands

#### CreateCategory

- **Type**: `Catalogue.CreateCategory.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attributes | Dict | No | — |
| name | String | Yes | max_length=100, min_length=1 |
| parent_category_id | Identifier | No | — |

#### DeactivateCategory

- **Type**: `Catalogue.DeactivateCategory.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| category_id | Identifier | Yes | min_length=1 |

#### ReorderCategory

- **Type**: `Catalogue.ReorderCategory.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| category_id | Identifier | Yes | min_length=1 |
| new_display_order | Integer | Yes | — |

#### UpdateCategory

- **Type**: `Catalogue.UpdateCategory.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attributes | Dict | No | — |
| category_id | Identifier | Yes | min_length=1 |
| name | String | No | max_length=100 |

## Product (`catalogue.product.product.Product`)

### Events

#### ProductActivated

- **Type**: `Catalogue.ProductActivated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| activated_at | DateTime | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| sku | String | Yes | max_length=255, min_length=1 |

#### ProductArchived

- **Type**: `Catalogue.ProductArchived.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| archived_at | DateTime | Yes | — |
| product_id | Identifier | Yes | min_length=1 |

#### ProductCreated

- **Type**: `Catalogue.ProductCreated.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| category_id | Identifier | No | — |
| created_at | DateTime | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| seller_id | Identifier | No | — |
| sku | String | Yes | max_length=255, min_length=1 |
| status | String | Yes | max_length=255, min_length=1 |
| title | String | Yes | max_length=255, min_length=1 |

#### ProductDetailsUpdated

- **Type**: `Catalogue.ProductDetailsUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| brand | String | No | max_length=255 |
| description | String | No | max_length=255 |
| product_id | Identifier | Yes | min_length=1 |
| title | String | Yes | max_length=255, min_length=1 |

#### ProductDiscontinued

- **Type**: `Catalogue.ProductDiscontinued.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| discontinued_at | DateTime | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| sku | String | Yes | max_length=255, min_length=1 |

#### ProductImageAdded

- **Type**: `Catalogue.ProductImageAdded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| image_id | Identifier | Yes | min_length=1 |
| is_primary | Boolean | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| url | String | Yes | max_length=255, min_length=1 |

#### ProductImageRemoved

- **Type**: `Catalogue.ProductImageRemoved.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| image_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |

#### TierPriceSet

- **Type**: `Catalogue.TierPriceSet.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| currency | String | Yes | max_length=255, min_length=1 |
| price | Float | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| tier | String | Yes | max_length=255, min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |

#### VariantAdded

- **Type**: `Catalogue.VariantAdded.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| created_at | DateTime | Yes | — |
| price_amount | Float | Yes | — |
| price_currency | String | Yes | max_length=255, min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |
| variant_sku | String | Yes | max_length=255, min_length=1 |

#### VariantPriceChanged

- **Type**: `Catalogue.VariantPriceChanged.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| currency | String | Yes | max_length=255, min_length=1 |
| new_price | Float | Yes | — |
| previous_price | Float | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |

### Commands

#### CreateProduct

- **Type**: `Catalogue.CreateProduct.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attributes | Dict | No | — |
| brand | String | No | max_length=100 |
| category_id | Identifier | No | — |
| description | String | No | max_length=255 |
| meta_description | String | No | max_length=160 |
| meta_title | String | No | max_length=70 |
| seller_id | Identifier | No | — |
| sku | String | Yes | max_length=50, min_length=1 |
| slug | String | No | max_length=200 |
| title | String | Yes | max_length=255, min_length=1 |
| visibility | String | No | max_length=20 |

#### UpdateProductDetails

- **Type**: `Catalogue.UpdateProductDetails.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attributes | Dict | No | — |
| brand | String | No | max_length=100 |
| description | String | No | max_length=255 |
| meta_description | String | No | max_length=160 |
| meta_title | String | No | max_length=70 |
| product_id | Identifier | Yes | min_length=1 |
| slug | String | No | max_length=200 |
| title | String | No | max_length=255 |

#### AddProductImage

- **Type**: `Catalogue.AddProductImage.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| alt_text | String | No | max_length=255 |
| is_primary | Boolean | No | — |
| product_id | Identifier | Yes | min_length=1 |
| url | String | Yes | max_length=500, min_length=1 |

#### RemoveProductImage

- **Type**: `Catalogue.RemoveProductImage.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| image_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |

#### ActivateProduct

- **Type**: `Catalogue.ActivateProduct.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| product_id | Identifier | Yes | min_length=1 |

#### ArchiveProduct

- **Type**: `Catalogue.ArchiveProduct.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| product_id | Identifier | Yes | min_length=1 |

#### DiscontinueProduct

- **Type**: `Catalogue.DiscontinueProduct.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| product_id | Identifier | Yes | min_length=1 |

#### AddVariant

- **Type**: `Catalogue.AddVariant.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attributes | Dict | No | — |
| base_price | Float | Yes | — |
| currency | String | No | max_length=3 |
| dimension_unit | String | No | max_length=2 |
| height | Float | No | — |
| length | Float | No | — |
| product_id | Identifier | Yes | min_length=1 |
| variant_sku | String | Yes | max_length=50, min_length=1 |
| weight_unit | String | No | max_length=2 |
| weight_value | Float | No | — |
| width | Float | No | — |

#### SetTierPrice

- **Type**: `Catalogue.SetTierPrice.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| price | Float | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| tier | String | Yes | max_length=50, min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |

#### UpdateVariantPrice

- **Type**: `Catalogue.UpdateVariantPrice.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| base_price | Float | Yes | — |
| currency | String | No | max_length=3 |
| product_id | Identifier | Yes | min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| ProductCreated | `Catalogue.ProductCreated.v1` | 1 |
| ProductDiscontinued | `Catalogue.ProductDiscontinued.v1` | 1 |
| VariantAdded | `Catalogue.VariantAdded.v1` | 1 |
