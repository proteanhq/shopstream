## Event Model: Category

> **Given** Category
> **When** CreateCategory, DeactivateCategory, ReorderCategory, UpdateCategory
> **Then** CategoryCreated, CategoryDeactivated, CategoryDetailsUpdated, CategoryReordered

```mermaid
flowchart LR
    subgraph catalogue_category_category_Category[Category]
        cmd_catalogue_category_management_CreateCategory[/CreateCategory/]
        cmd_catalogue_category_management_DeactivateCategory[/DeactivateCategory/]
        cmd_catalogue_category_management_ReorderCategory[/ReorderCategory/]
        cmd_catalogue_category_management_UpdateCategory[/UpdateCategory/]
        agg_catalogue_category_category_Category[Category]
        evt_catalogue_category_events_CategoryCreated([CategoryCreated])
        evt_catalogue_category_events_CategoryDeactivated([CategoryDeactivated])
        evt_catalogue_category_events_CategoryDetailsUpdated([CategoryDetailsUpdated])
        evt_catalogue_category_events_CategoryReordered([CategoryReordered])
        rm_catalogue_category_category_Category_catalogue_projections_category_products_CategoryProductsProjector[(CategoryProductsProjector → CategoryProducts)]
        rm_catalogue_category_category_Category_catalogue_projections_category_tree_CategoryTreeProjector[(CategoryTreeProjector → CategoryTree)]
    end
    cmd_catalogue_category_management_CreateCategory --> agg_catalogue_category_category_Category
    cmd_catalogue_category_management_DeactivateCategory --> agg_catalogue_category_category_Category
    cmd_catalogue_category_management_ReorderCategory --> agg_catalogue_category_category_Category
    cmd_catalogue_category_management_UpdateCategory --> agg_catalogue_category_category_Category
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryCreated
    evt_catalogue_category_events_CategoryCreated --> rm_catalogue_category_category_Category_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_category_events_CategoryCreated --> rm_catalogue_category_category_Category_catalogue_projections_category_tree_CategoryTreeProjector
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryDeactivated
    evt_catalogue_category_events_CategoryDeactivated --> rm_catalogue_category_category_Category_catalogue_projections_category_tree_CategoryTreeProjector
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryDetailsUpdated
    evt_catalogue_category_events_CategoryDetailsUpdated --> rm_catalogue_category_category_Category_catalogue_projections_category_tree_CategoryTreeProjector
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryReordered
    evt_catalogue_category_events_CategoryReordered --> rm_catalogue_category_category_Category_catalogue_projections_category_tree_CategoryTreeProjector
```

## Event Model: Product

> **Given** Product
> **When** CreateProduct, UpdateProductDetails, AddProductImage, RemoveProductImage, ActivateProduct, ArchiveProduct, DiscontinueProduct, AddVariant, SetTierPrice, UpdateVariantPrice
> **Then** ProductActivated, ProductArchived, ProductCreated, ProductDetailsUpdated, ProductDiscontinued, ProductImageAdded, ProductImageRemoved, TierPriceSet, VariantAdded, VariantPriceChanged

```mermaid
flowchart LR
    subgraph catalogue_product_product_Product[Product]
        cmd_catalogue_product_creation_CreateProduct[/CreateProduct/]
        cmd_catalogue_product_details_UpdateProductDetails[/UpdateProductDetails/]
        cmd_catalogue_product_images_AddProductImage[/AddProductImage/]
        cmd_catalogue_product_images_RemoveProductImage[/RemoveProductImage/]
        cmd_catalogue_product_lifecycle_ActivateProduct[/ActivateProduct/]
        cmd_catalogue_product_lifecycle_ArchiveProduct[/ArchiveProduct/]
        cmd_catalogue_product_lifecycle_DiscontinueProduct[/DiscontinueProduct/]
        cmd_catalogue_product_variants_AddVariant[/AddVariant/]
        cmd_catalogue_product_variants_SetTierPrice[/SetTierPrice/]
        cmd_catalogue_product_variants_UpdateVariantPrice[/UpdateVariantPrice/]
        agg_catalogue_product_product_Product[Product]
        evt_catalogue_product_events_ProductActivated([ProductActivated])
        evt_catalogue_product_events_ProductArchived([ProductArchived])
        evt_catalogue_product_events_ProductCreated([ProductCreated])
        evt_catalogue_product_events_ProductDetailsUpdated([ProductDetailsUpdated])
        evt_catalogue_product_events_ProductDiscontinued([ProductDiscontinued])
        evt_catalogue_product_events_ProductImageAdded([ProductImageAdded])
        evt_catalogue_product_events_ProductImageRemoved([ProductImageRemoved])
        evt_catalogue_product_events_TierPriceSet([TierPriceSet])
        evt_catalogue_product_events_VariantAdded([VariantAdded])
        evt_catalogue_product_events_VariantPriceChanged([VariantPriceChanged])
        rm_catalogue_product_product_Product_catalogue_projections_category_products_CategoryProductsProjector[(CategoryProductsProjector → CategoryProducts)]
        rm_catalogue_product_product_Product_catalogue_projections_category_tree_CategoryTreeProjector[(CategoryTreeProjector → CategoryTree)]
        rm_catalogue_product_product_Product_catalogue_projections_price_history_PriceHistoryProjector[(PriceHistoryProjector → PriceHistory)]
        rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector[(ProductCardProjector → ProductCard)]
        rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector[(ProductDetailProjector → ProductDetail)]
        rm_catalogue_product_product_Product_catalogue_projections_seller_catalogue_SellerCatalogueProjector[(SellerCatalogueProjector → SellerCatalogue)]
    end
    cmd_catalogue_product_creation_CreateProduct --> agg_catalogue_product_product_Product
    cmd_catalogue_product_details_UpdateProductDetails --> agg_catalogue_product_product_Product
    cmd_catalogue_product_images_AddProductImage --> agg_catalogue_product_product_Product
    cmd_catalogue_product_images_RemoveProductImage --> agg_catalogue_product_product_Product
    cmd_catalogue_product_lifecycle_ActivateProduct --> agg_catalogue_product_product_Product
    cmd_catalogue_product_lifecycle_ArchiveProduct --> agg_catalogue_product_product_Product
    cmd_catalogue_product_lifecycle_DiscontinueProduct --> agg_catalogue_product_product_Product
    cmd_catalogue_product_variants_AddVariant --> agg_catalogue_product_product_Product
    cmd_catalogue_product_variants_SetTierPrice --> agg_catalogue_product_product_Product
    cmd_catalogue_product_variants_UpdateVariantPrice --> agg_catalogue_product_product_Product
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductActivated
    evt_catalogue_product_events_ProductActivated --> rm_catalogue_product_product_Product_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductActivated --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductActivated --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductActivated --> rm_catalogue_product_product_Product_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductArchived
    evt_catalogue_product_events_ProductArchived --> rm_catalogue_product_product_Product_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductArchived --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductArchived --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductArchived --> rm_catalogue_product_product_Product_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductCreated
    evt_catalogue_product_events_ProductCreated --> rm_catalogue_product_product_Product_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductCreated --> rm_catalogue_product_product_Product_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_product_events_ProductCreated --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductCreated --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductCreated --> rm_catalogue_product_product_Product_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductDetailsUpdated
    evt_catalogue_product_events_ProductDetailsUpdated --> rm_catalogue_product_product_Product_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductDetailsUpdated --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductDetailsUpdated --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductDetailsUpdated --> rm_catalogue_product_product_Product_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductDiscontinued
    evt_catalogue_product_events_ProductDiscontinued --> rm_catalogue_product_product_Product_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductDiscontinued --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductDiscontinued --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductDiscontinued --> rm_catalogue_product_product_Product_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductImageAdded
    evt_catalogue_product_events_ProductImageAdded --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductImageAdded --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductImageRemoved
    evt_catalogue_product_events_ProductImageRemoved --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductImageRemoved --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_TierPriceSet
    evt_catalogue_product_events_TierPriceSet --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_VariantAdded
    evt_catalogue_product_events_VariantAdded --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_VariantAdded --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_VariantAdded --> rm_catalogue_product_product_Product_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_VariantPriceChanged
    evt_catalogue_product_events_VariantPriceChanged --> rm_catalogue_product_product_Product_catalogue_projections_price_history_PriceHistoryProjector
    evt_catalogue_product_events_VariantPriceChanged --> rm_catalogue_product_product_Product_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_VariantPriceChanged --> rm_catalogue_product_product_Product_catalogue_projections_product_detail_ProductDetailProjector
```
