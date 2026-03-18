# Catalogue Domain

Products, variants, categories, and pricing.

## Domain Composition Root

`domain.py` — `catalogue = Domain(name="catalogue")`

All elements register via `@catalogue.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker, Message DB event store. Environment overlays for test (`catalogue_test` DB) and production (`catalogue` DB, async events).

## Aggregate: Product

**File:** `product/product.py`

Root fields: `sku` (SKU VO), `seller_id`, `title`, `description`, `category_id`, `brand`, `attributes` (JSON text), `variants` (HasMany Variant), `images` (HasMany Image), `status` (ProductStatus enum), `visibility` (ProductVisibility enum), `seo` (SEO VO), `created_at`, `updated_at`.

### Enums
- `ProductStatus`: Draft → Active → Discontinued → Archived (state machine)
- `ProductVisibility`: Public, Unlisted, Tier_Restricted

### Value Objects (part_of="Product")
- `Price` — base_price, currency (default "USD"), tier_prices (JSON text with validation)
- `SEO` — meta_title, meta_description, slug (URL-safe validation)
- `Dimensions` — length, width, height, unit (cm/in)
- `Weight` — value, unit (kg/lb/g/oz)

### Entities (part_of="Product")
- `Variant` — variant_sku (SKU VO), attributes, price (Price VO), weight (Weight VO), dimensions (Dimensions VO), is_active
- `Image` — url, alt_text, is_primary, display_order

### Shared Value Objects (`shared/`)
- `SKU` (`shared/sku.py`) — code field, 3-50 chars, alphanumeric + hyphens, no leading/trailing/consecutive hyphens

### Invariants
- `images_cannot_exceed_maximum` — max 10 images
- `exactly_one_primary_image_when_images_exist` — exactly one primary when any exist

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Product.create(...)` | Class method, creates in Draft status, raises `ProductCreated` |
| `update_details(...)` | Partial update of title/description/brand/attributes/seo, raises `ProductDetailsUpdated` |
| `add_variant(...)` | Creates Variant with SKU + Price VOs, raises `VariantAdded` |
| `update_variant_price(variant_id, new_price)` | Replaces Price VO, raises `VariantPriceChanged` |
| `set_tier_price(variant_id, tier, price)` | Merges tier into Price.tier_prices JSON, raises `TierPriceSet` |
| `add_image(...)` | First image auto-primary, uses `atomic_change`, raises `ProductImageAdded` |
| `remove_image(image_id)` | Reassigns primary if needed, raises `ProductImageRemoved` |
| `activate()` | Draft → Active (requires variants), raises `ProductActivated` |
| `discontinue()` | Active → Discontinued, raises `ProductDiscontinued` |
| `archive()` | Discontinued → Archived, raises `ProductArchived` |

## Aggregate: Category

**File:** `category/category.py`

Root fields: `name`, `parent_category_id`, `level` (0-4), `attributes` (JSON text), `is_active`, `display_order`, `created_at`, `updated_at`.

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Category.create(...)` | Class method, raises `CategoryCreated` |
| `update_details(name?, attributes?)` | Partial update, raises `CategoryDetailsUpdated` |
| `reorder(new_display_order)` | Updates display_order, raises `CategoryReordered` |
| `deactivate()` | Only from active, raises `CategoryDeactivated` |

## Events

**Product events** (`product/events.py`): `ProductCreated`, `ProductDetailsUpdated`, `VariantAdded`, `VariantPriceChanged`, `TierPriceSet`, `ProductImageAdded`, `ProductImageRemoved`, `ProductActivated`, `ProductDiscontinued`, `ProductArchived`

**Category events** (`category/events.py`): `CategoryCreated`, `CategoryDetailsUpdated`, `CategoryReordered`, `CategoryDeactivated`

## Commands & Handlers

| File | Commands |
|------|---------|
| `product/creation.py` | `CreateProduct` → `CreateProductHandler` |
| `product/details.py` | `UpdateProductDetails` → `UpdateProductDetailsHandler` |
| `product/variants.py` | `AddVariant`, `UpdateVariantPrice`, `SetTierPrice` → `VariantHandler` |
| `product/images.py` | `AddProductImage`, `RemoveProductImage` → `ProductImageHandler` |
| `product/lifecycle.py` | `ActivateProduct`, `DiscontinueProduct`, `ArchiveProduct` → `ProductLifecycleHandler` |
| `category/management.py` | `CreateCategory`, `UpdateCategory`, `ReorderCategory`, `DeactivateCategory` → handlers |

## Projections

**Directory:** `projections/`

| File | Projection | Purpose |
|------|-----------|---------|
| `product_card.py` | `ProductCard` | Listing/search view (title, price range, primary image, status) |
| `product_detail.py` | `ProductDetail` | Full product view with variants and images |
| `seller_catalogue.py` | `SellerCatalogue` | Products grouped by seller |
| `price_history.py` | `PriceHistory` | Price change tracking |
| `category_tree.py` | `CategoryTree` | Hierarchical category view |

## API

**Package:** `api/`

| File | Contents |
|------|----------|
| `api/__init__.py` | Re-exports `product_router` and `category_router` |
| `api/schemas.py` | Pydantic request/response models (external contract) |
| `api/routes.py` | 14 endpoints (10 product + 4 category) |

### Product Endpoints (`tags=["products"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/products` | `CreateProductRequest` | `ProductIdResponse` (201) |
| PUT | `/products/{id}/details` | `UpdateProductDetailsRequest` | `StatusResponse` |
| POST | `/products/{id}/variants` | `AddVariantRequest` | `StatusResponse` (201) |
| PUT | `/products/{id}/variants/{vid}/price` | `UpdateVariantPriceRequest` | `StatusResponse` |
| POST | `/products/{id}/variants/{vid}/tier-price` | `SetTierPriceRequest` | `StatusResponse` (201) |
| POST | `/products/{id}/images` | `AddProductImageRequest` | `StatusResponse` (201) |
| DELETE | `/products/{id}/images/{iid}` | — | `StatusResponse` |
| PUT | `/products/{id}/activate` | — | `StatusResponse` |
| PUT | `/products/{id}/discontinue` | — | `StatusResponse` |
| PUT | `/products/{id}/archive` | — | `StatusResponse` |

### Category Endpoints (`tags=["categories"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/categories` | `CreateCategoryRequest` | `CategoryIdResponse` (201) |
| PUT | `/categories/{id}` | `UpdateCategoryRequest` | `StatusResponse` |
| PUT | `/categories/{id}/reorder` | `ReorderCategoryRequest` | `StatusResponse` |
| PUT | `/categories/{id}/deactivate` | — | `StatusResponse` |
