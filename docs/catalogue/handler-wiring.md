## Command Handlers: Category

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_catalogue_category_management_ManageCategoryHandler[ManageCategoryHandler]
    end
    cmd_catalogue_category_management_CreateCategory[/CreateCategory/] --> ch_catalogue_category_management_ManageCategoryHandler
    cmd_catalogue_category_management_DeactivateCategory[/DeactivateCategory/] --> ch_catalogue_category_management_ManageCategoryHandler
    cmd_catalogue_category_management_ReorderCategory[/ReorderCategory/] --> ch_catalogue_category_management_ManageCategoryHandler
    cmd_catalogue_category_management_UpdateCategory[/UpdateCategory/] --> ch_catalogue_category_management_ManageCategoryHandler
    ch_catalogue_category_management_ManageCategoryHandler --> agg_catalogue_category_category_Category[Category]
```

## Command Handlers: Product

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_catalogue_product_creation_CreateProductHandler[CreateProductHandler]
        ch_catalogue_product_details_ManageProductDetailsHandler[ManageProductDetailsHandler]
        ch_catalogue_product_images_ManageImagesHandler[ManageImagesHandler]
        ch_catalogue_product_lifecycle_ManageLifecycleHandler[ManageLifecycleHandler]
        ch_catalogue_product_variants_ManageVariantsHandler[ManageVariantsHandler]
    end
    cmd_catalogue_product_creation_CreateProduct[/CreateProduct/] --> ch_catalogue_product_creation_CreateProductHandler
    ch_catalogue_product_creation_CreateProductHandler --> agg_catalogue_product_product_Product[Product]
    cmd_catalogue_product_details_UpdateProductDetails[/UpdateProductDetails/] --> ch_catalogue_product_details_ManageProductDetailsHandler
    ch_catalogue_product_details_ManageProductDetailsHandler --> agg_catalogue_product_product_Product[Product]
    cmd_catalogue_product_images_AddProductImage[/AddProductImage/] --> ch_catalogue_product_images_ManageImagesHandler
    cmd_catalogue_product_images_RemoveProductImage[/RemoveProductImage/] --> ch_catalogue_product_images_ManageImagesHandler
    ch_catalogue_product_images_ManageImagesHandler --> agg_catalogue_product_product_Product[Product]
    cmd_catalogue_product_lifecycle_ActivateProduct[/ActivateProduct/] --> ch_catalogue_product_lifecycle_ManageLifecycleHandler
    cmd_catalogue_product_lifecycle_ArchiveProduct[/ArchiveProduct/] --> ch_catalogue_product_lifecycle_ManageLifecycleHandler
    cmd_catalogue_product_lifecycle_DiscontinueProduct[/DiscontinueProduct/] --> ch_catalogue_product_lifecycle_ManageLifecycleHandler
    ch_catalogue_product_lifecycle_ManageLifecycleHandler --> agg_catalogue_product_product_Product[Product]
    cmd_catalogue_product_variants_AddVariant[/AddVariant/] --> ch_catalogue_product_variants_ManageVariantsHandler
    cmd_catalogue_product_variants_SetTierPrice[/SetTierPrice/] --> ch_catalogue_product_variants_ManageVariantsHandler
    cmd_catalogue_product_variants_UpdateVariantPrice[/UpdateVariantPrice/] --> ch_catalogue_product_variants_ManageVariantsHandler
    ch_catalogue_product_variants_ManageVariantsHandler --> agg_catalogue_product_product_Product[Product]
```

## Projector: CategoryProducts

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_catalogue_projections_category_products_CategoryProductsProjector[CategoryProductsProjector → CategoryProducts]
    end
    evt_catalogue_category_events_CategoryCreated([CategoryCreated]) --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductActivated([ProductActivated]) --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductArchived([ProductArchived]) --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductCreated([ProductCreated]) --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductDetailsUpdated([ProductDetailsUpdated]) --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductDiscontinued([ProductDiscontinued]) --> proj_catalogue_projections_category_products_CategoryProductsProjector
```

## Projector: CategoryTree

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_catalogue_projections_category_tree_CategoryTreeProjector[CategoryTreeProjector → CategoryTree]
    end
    evt_catalogue_category_events_CategoryCreated([CategoryCreated]) --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_category_events_CategoryDeactivated([CategoryDeactivated]) --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_category_events_CategoryDetailsUpdated([CategoryDetailsUpdated]) --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_category_events_CategoryReordered([CategoryReordered]) --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_product_events_ProductCreated([ProductCreated]) --> proj_catalogue_projections_category_tree_CategoryTreeProjector
```

## Projector: PriceHistory

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_catalogue_projections_price_history_PriceHistoryProjector[PriceHistoryProjector → PriceHistory]
    end
    evt_catalogue_product_events_VariantPriceChanged([VariantPriceChanged]) --> proj_catalogue_projections_price_history_PriceHistoryProjector
```

## Projector: ProductCard

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_catalogue_projections_product_card_ProductCardProjector[ProductCardProjector → ProductCard]
    end
    evt_catalogue_product_events_ProductActivated([ProductActivated]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductArchived([ProductArchived]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductCreated([ProductCreated]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductDetailsUpdated([ProductDetailsUpdated]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductDiscontinued([ProductDiscontinued]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductImageAdded([ProductImageAdded]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductImageRemoved([ProductImageRemoved]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_VariantAdded([VariantAdded]) --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_VariantPriceChanged([VariantPriceChanged]) --> proj_catalogue_projections_product_card_ProductCardProjector
```

## Projector: ProductDetail

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_catalogue_projections_product_detail_ProductDetailProjector[ProductDetailProjector → ProductDetail]
    end
    evt_catalogue_product_events_ProductActivated([ProductActivated]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductArchived([ProductArchived]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductCreated([ProductCreated]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductDetailsUpdated([ProductDetailsUpdated]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductDiscontinued([ProductDiscontinued]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductImageAdded([ProductImageAdded]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductImageRemoved([ProductImageRemoved]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_TierPriceSet([TierPriceSet]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_VariantAdded([VariantAdded]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_VariantPriceChanged([VariantPriceChanged]) --> proj_catalogue_projections_product_detail_ProductDetailProjector
```

## Projector: SellerCatalogue

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector[SellerCatalogueProjector → SellerCatalogue]
    end
    evt_catalogue_product_events_ProductActivated([ProductActivated]) --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductArchived([ProductArchived]) --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductCreated([ProductCreated]) --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductDetailsUpdated([ProductDetailsUpdated]) --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductDiscontinued([ProductDiscontinued]) --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_VariantAdded([VariantAdded]) --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
```
