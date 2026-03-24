## Event Flows

```mermaid
flowchart LR
    subgraph abc_DefaultOutbox[DefaultOutbox]
        agg_abc_DefaultOutbox[DefaultOutbox]
    end
    subgraph abc_MemoryOutbox[MemoryOutbox]
        agg_abc_MemoryOutbox[MemoryOutbox]
    end
    subgraph catalogue_category_category_Category[Category]
        agg_catalogue_category_category_Category[Category]
        cmd_catalogue_category_management_CreateCategory[/CreateCategory/]
        cmd_catalogue_category_management_DeactivateCategory[/DeactivateCategory/]
        cmd_catalogue_category_management_ReorderCategory[/ReorderCategory/]
        cmd_catalogue_category_management_UpdateCategory[/UpdateCategory/]
        evt_catalogue_category_events_CategoryCreated([CategoryCreated])
        evt_catalogue_category_events_CategoryDeactivated([CategoryDeactivated])
        evt_catalogue_category_events_CategoryDetailsUpdated([CategoryDetailsUpdated])
        evt_catalogue_category_events_CategoryReordered([CategoryReordered])
        hdlr_catalogue_category_management_ManageCategoryHandler[ManageCategoryHandler]
    end
    subgraph catalogue_product_product_Product[Product]
        agg_catalogue_product_product_Product[Product]
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
        hdlr_catalogue_product_creation_CreateProductHandler[CreateProductHandler]
        hdlr_catalogue_product_details_ManageProductDetailsHandler[ManageProductDetailsHandler]
        hdlr_catalogue_product_images_ManageImagesHandler[ManageImagesHandler]
        hdlr_catalogue_product_lifecycle_ManageLifecycleHandler[ManageLifecycleHandler]
        hdlr_catalogue_product_variants_ManageVariantsHandler[ManageVariantsHandler]
    end
    cmd_catalogue_category_management_CreateCategory --> hdlr_catalogue_category_management_ManageCategoryHandler
    cmd_catalogue_category_management_DeactivateCategory --> hdlr_catalogue_category_management_ManageCategoryHandler
    cmd_catalogue_category_management_ReorderCategory --> hdlr_catalogue_category_management_ManageCategoryHandler
    cmd_catalogue_category_management_UpdateCategory --> hdlr_catalogue_category_management_ManageCategoryHandler
    hdlr_catalogue_category_management_ManageCategoryHandler --> agg_catalogue_category_category_Category
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryCreated
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryDeactivated
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryDetailsUpdated
    agg_catalogue_category_category_Category --> evt_catalogue_category_events_CategoryReordered
    cmd_catalogue_product_creation_CreateProduct --> hdlr_catalogue_product_creation_CreateProductHandler
    hdlr_catalogue_product_creation_CreateProductHandler --> agg_catalogue_product_product_Product
    cmd_catalogue_product_details_UpdateProductDetails --> hdlr_catalogue_product_details_ManageProductDetailsHandler
    hdlr_catalogue_product_details_ManageProductDetailsHandler --> agg_catalogue_product_product_Product
    cmd_catalogue_product_images_AddProductImage --> hdlr_catalogue_product_images_ManageImagesHandler
    cmd_catalogue_product_images_RemoveProductImage --> hdlr_catalogue_product_images_ManageImagesHandler
    hdlr_catalogue_product_images_ManageImagesHandler --> agg_catalogue_product_product_Product
    cmd_catalogue_product_lifecycle_ActivateProduct --> hdlr_catalogue_product_lifecycle_ManageLifecycleHandler
    cmd_catalogue_product_lifecycle_ArchiveProduct --> hdlr_catalogue_product_lifecycle_ManageLifecycleHandler
    cmd_catalogue_product_lifecycle_DiscontinueProduct --> hdlr_catalogue_product_lifecycle_ManageLifecycleHandler
    hdlr_catalogue_product_lifecycle_ManageLifecycleHandler --> agg_catalogue_product_product_Product
    cmd_catalogue_product_variants_AddVariant --> hdlr_catalogue_product_variants_ManageVariantsHandler
    cmd_catalogue_product_variants_SetTierPrice --> hdlr_catalogue_product_variants_ManageVariantsHandler
    cmd_catalogue_product_variants_UpdateVariantPrice --> hdlr_catalogue_product_variants_ManageVariantsHandler
    hdlr_catalogue_product_variants_ManageVariantsHandler --> agg_catalogue_product_product_Product
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductActivated
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductArchived
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductCreated
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductDetailsUpdated
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductDiscontinued
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductImageAdded
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_ProductImageRemoved
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_TierPriceSet
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_VariantAdded
    agg_catalogue_product_product_Product --> evt_catalogue_product_events_VariantPriceChanged
    proj_catalogue_projections_category_products_CategoryProductsProjector[CategoryProductsProjector → CategoryProducts]
    evt_catalogue_category_events_CategoryCreated --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductActivated --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductArchived --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductCreated --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductDetailsUpdated --> proj_catalogue_projections_category_products_CategoryProductsProjector
    evt_catalogue_product_events_ProductDiscontinued --> proj_catalogue_projections_category_products_CategoryProductsProjector
    proj_catalogue_projections_category_tree_CategoryTreeProjector[CategoryTreeProjector → CategoryTree]
    evt_catalogue_category_events_CategoryCreated --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_category_events_CategoryDeactivated --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_category_events_CategoryDetailsUpdated --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_category_events_CategoryReordered --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    evt_catalogue_product_events_ProductCreated --> proj_catalogue_projections_category_tree_CategoryTreeProjector
    proj_catalogue_projections_price_history_PriceHistoryProjector[PriceHistoryProjector → PriceHistory]
    evt_catalogue_product_events_VariantPriceChanged --> proj_catalogue_projections_price_history_PriceHistoryProjector
    proj_catalogue_projections_product_card_ProductCardProjector[ProductCardProjector → ProductCard]
    evt_catalogue_product_events_ProductActivated --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductArchived --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductCreated --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductDetailsUpdated --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductDiscontinued --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductImageAdded --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_ProductImageRemoved --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_VariantAdded --> proj_catalogue_projections_product_card_ProductCardProjector
    evt_catalogue_product_events_VariantPriceChanged --> proj_catalogue_projections_product_card_ProductCardProjector
    proj_catalogue_projections_product_detail_ProductDetailProjector[ProductDetailProjector → ProductDetail]
    evt_catalogue_product_events_ProductActivated --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductArchived --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductCreated --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductDetailsUpdated --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductDiscontinued --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductImageAdded --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_ProductImageRemoved --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_TierPriceSet --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_VariantAdded --> proj_catalogue_projections_product_detail_ProductDetailProjector
    evt_catalogue_product_events_VariantPriceChanged --> proj_catalogue_projections_product_detail_ProductDetailProjector
    proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector[SellerCatalogueProjector → SellerCatalogue]
    evt_catalogue_product_events_ProductActivated --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductArchived --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductCreated --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductDetailsUpdated --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_ProductDiscontinued --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
    evt_catalogue_product_events_VariantAdded --> proj_catalogue_projections_seller_catalogue_SellerCatalogueProjector
```
