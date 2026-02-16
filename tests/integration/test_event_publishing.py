"""Cross-domain event publishing verification tests.

These tests verify that events raised by aggregates in both the Identity
and Catalogue domains are correctly stored in the outbox table during
UnitOfWork commit. The OutboxProcessor (run by the Engine) later reads
these records and publishes them to Redis Streams.

Test strategy:
  - We test the *synchronous* half: command → aggregate mutation → event
    stored in outbox.  This requires a running PostgreSQL database but not
    a running Engine or Redis.
  - The outbox record structure is validated to ensure the Engine can
    publish it downstream without modification.
"""

from protean import current_domain
from protean.utils.outbox import OutboxStatus


# ---------------------------------------------------------------------------
# Identity domain: outbox tests
# ---------------------------------------------------------------------------
class TestIdentityEventOutbox:
    """Verify that Identity domain events land in the outbox."""

    def test_customer_registered_event_in_outbox(self, identity_ctx):
        """RegisterCustomer → CustomerRegistered event stored in outbox."""
        from identity.customer.registration import RegisterCustomer

        command = RegisterCustomer(
            external_id="EXT-OBX-001",
            email="outbox-test@example.com",
            first_name="Outbox",
            last_name="Test",
        )
        customer_id = current_domain.process(command, asynchronous=False)
        assert customer_id is not None

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        registered_events = [r for r in records if r.type == "Identity.CustomerRegistered.v1"]
        assert len(registered_events) == 1

        record = registered_events[0]
        assert record.status == OutboxStatus.PENDING.value
        assert record.data["customer_id"] == customer_id
        assert record.data["email"] == "outbox-test@example.com"
        assert record.data["first_name"] == "Outbox"
        assert record.data["last_name"] == "Test"
        assert record.stream_name.startswith("identity::customer-")

    def test_account_suspended_event_in_outbox(self, identity_ctx):
        """SuspendAccount → AccountSuspended event stored in outbox."""
        from identity.customer.account import SuspendAccount
        from identity.customer.registration import RegisterCustomer

        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-SUSP-001",
                email="suspend@example.com",
                first_name="Suspend",
                last_name="Test",
            ),
            asynchronous=False,
        )

        current_domain.process(
            SuspendAccount(customer_id=customer_id, reason="Fraud investigation"),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        suspended_events = [r for r in records if r.type == "Identity.AccountSuspended.v1"]
        assert len(suspended_events) == 1

        record = suspended_events[0]
        assert record.data["customer_id"] == customer_id
        assert record.data["reason"] == "Fraud investigation"
        assert record.stream_name.startswith("identity::customer-")

    def test_tier_upgraded_event_in_outbox(self, identity_ctx):
        """UpgradeTier → TierUpgraded event stored in outbox."""
        from identity.customer.registration import RegisterCustomer
        from identity.customer.tier import UpgradeTier

        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-TIER-001",
                email="tier@example.com",
                first_name="Tier",
                last_name="Test",
            ),
            asynchronous=False,
        )

        current_domain.process(
            UpgradeTier(customer_id=customer_id, new_tier="Silver"),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        tier_events = [r for r in records if r.type == "Identity.TierUpgraded.v1"]
        assert len(tier_events) == 1

        record = tier_events[0]
        assert record.data["customer_id"] == customer_id
        assert record.data["previous_tier"] == "Standard"
        assert record.data["new_tier"] == "Silver"

    def test_multiple_identity_events_from_lifecycle(self, identity_ctx):
        """Full account lifecycle produces multiple outbox records."""
        from identity.customer.account import CloseAccount, SuspendAccount
        from identity.customer.registration import RegisterCustomer

        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-MULTI-001",
                email="multi@example.com",
                first_name="Multi",
                last_name="Event",
            ),
            asynchronous=False,
        )

        current_domain.process(
            SuspendAccount(customer_id=customer_id, reason="Review"),
            asynchronous=False,
        )

        current_domain.process(
            CloseAccount(customer_id=customer_id),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        event_types = {r.type for r in records}
        assert "Identity.CustomerRegistered.v1" in event_types
        assert "Identity.AccountSuspended.v1" in event_types
        assert "Identity.AccountClosed.v1" in event_types

    def test_identity_outbox_record_metadata(self, identity_ctx):
        """Outbox records carry correct metadata for the Engine."""
        from identity.customer.registration import RegisterCustomer

        current_domain.process(
            RegisterCustomer(
                external_id="EXT-META-001",
                email="meta@example.com",
                first_name="Meta",
                last_name="Test",
            ),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()
        record = next(r for r in records if r.type == "Identity.CustomerRegistered.v1")

        assert record.message_id is not None
        assert record.metadata_ is not None
        assert record.created_at is not None
        assert record.retry_count == 0
        assert record.status == OutboxStatus.PENDING.value


# ---------------------------------------------------------------------------
# Catalogue domain: outbox tests
# ---------------------------------------------------------------------------
class TestCatalogueEventOutbox:
    """Verify that Catalogue domain events land in the outbox."""

    def test_product_created_event_in_outbox(self, catalogue_ctx):
        """CreateProduct → ProductCreated event stored in outbox."""
        from catalogue.product.creation import CreateProduct

        command = CreateProduct(
            sku="OBX-PROD-001",
            title="Outbox Test Product",
            seller_id="seller-obx",
            category_id="cat-obx",
        )
        product_id = current_domain.process(command, asynchronous=False)
        assert product_id is not None

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        created_events = [r for r in records if r.type == "Catalogue.ProductCreated.v1"]
        assert len(created_events) == 1

        record = created_events[0]
        assert record.status == OutboxStatus.PENDING.value
        assert record.data["product_id"] == product_id
        assert record.data["sku"] == "OBX-PROD-001"
        assert record.data["title"] == "Outbox Test Product"
        assert record.stream_name.startswith("catalogue::product-")

    def test_variant_added_event_in_outbox(self, catalogue_ctx):
        """AddVariant → VariantAdded event stored in outbox."""
        from catalogue.product.creation import CreateProduct
        from catalogue.product.variants import AddVariant

        product_id = current_domain.process(
            CreateProduct(
                sku="OBX-VAR-001",
                title="Variant Test Product",
                seller_id="seller-var",
            ),
            asynchronous=False,
        )

        current_domain.process(
            AddVariant(
                product_id=product_id,
                variant_sku="VAR-SKU-001",
                attributes='{"size": "L", "color": "Blue"}',
                base_price=29.99,
                currency="USD",
            ),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        variant_events = [r for r in records if r.type == "Catalogue.VariantAdded.v1"]
        assert len(variant_events) == 1

        record = variant_events[0]
        assert record.data["product_id"] == product_id
        assert record.data["variant_sku"] == "VAR-SKU-001"

    def test_product_lifecycle_events_in_outbox(self, catalogue_ctx):
        """Product lifecycle transitions produce outbox records."""
        from catalogue.product.creation import CreateProduct
        from catalogue.product.lifecycle import ActivateProduct, DiscontinueProduct
        from catalogue.product.variants import AddVariant

        product_id = current_domain.process(
            CreateProduct(
                sku="OBX-LIFE-001",
                title="Lifecycle Test Product",
                seller_id="seller-life",
            ),
            asynchronous=False,
        )

        current_domain.process(
            AddVariant(
                product_id=product_id,
                variant_sku="LIFE-VAR-001",
                attributes='{"size": "M"}',
                base_price=19.99,
                currency="USD",
            ),
            asynchronous=False,
        )

        current_domain.process(
            ActivateProduct(product_id=product_id),
            asynchronous=False,
        )

        current_domain.process(
            DiscontinueProduct(product_id=product_id),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        event_types = {r.type for r in records}
        assert "Catalogue.ProductCreated.v1" in event_types
        assert "Catalogue.VariantAdded.v1" in event_types
        assert "Catalogue.ProductActivated.v1" in event_types
        assert "Catalogue.ProductDiscontinued.v1" in event_types

    def test_category_created_event_in_outbox(self, catalogue_ctx):
        """CreateCategory → CategoryCreated event stored in outbox."""
        from catalogue.category.management import CreateCategory

        current_domain.process(
            CreateCategory(name="Outbox Test Category"),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        category_events = [r for r in records if r.type == "Catalogue.CategoryCreated.v1"]
        assert len(category_events) == 1
        assert category_events[0].data["name"] == "Outbox Test Category"

    def test_catalogue_outbox_record_metadata(self, catalogue_ctx):
        """Catalogue outbox records carry correct metadata."""
        from catalogue.product.creation import CreateProduct

        current_domain.process(
            CreateProduct(
                sku="OBX-META-001",
                title="Meta Test Product",
            ),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()
        record = next(r for r in records if r.type == "Catalogue.ProductCreated.v1")

        assert record.message_id is not None
        assert record.metadata_ is not None
        assert record.created_at is not None
        assert record.retry_count == 0
        assert record.status == OutboxStatus.PENDING.value


# ---------------------------------------------------------------------------
# Event payload integrity
# ---------------------------------------------------------------------------
class TestEventPayloadIntegrity:
    """Verify outbox records contain all expected fields with correct values."""

    def test_customer_registered_payload_complete(self, identity_ctx):
        """CustomerRegistered outbox record has all required fields."""
        from identity.customer.registration import RegisterCustomer

        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-PAYLOAD-001",
                email="payload@example.com",
                first_name="Payload",
                last_name="Check",
                phone="+1-555-999-0000",
            ),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()
        record = next(r for r in records if r.type == "Identity.CustomerRegistered.v1")

        data = record.data
        assert data["customer_id"] == customer_id
        assert data["external_id"] == "EXT-PAYLOAD-001"
        assert data["email"] == "payload@example.com"
        assert data["first_name"] == "Payload"
        assert data["last_name"] == "Check"
        assert data["registered_at"] is not None

    def test_product_created_payload_complete(self, catalogue_ctx):
        """ProductCreated outbox record has all required fields."""
        from catalogue.product.creation import CreateProduct

        product_id = current_domain.process(
            CreateProduct(
                sku="PAYLOAD-001",
                title="Payload Check Product",
                seller_id="seller-payload",
                category_id="cat-payload",
                brand="TestBrand",
            ),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()
        record = next(r for r in records if r.type == "Catalogue.ProductCreated.v1")

        data = record.data
        assert data["product_id"] == product_id
        assert data["sku"] == "PAYLOAD-001"
        assert data["title"] == "Payload Check Product"
        assert data["status"] == "Draft"
        assert data["created_at"] is not None

    def test_variant_price_changed_payload(self, catalogue_ctx):
        """VariantPriceChanged outbox record captures old and new prices."""
        from catalogue.product.creation import CreateProduct
        from catalogue.product.variants import AddVariant, UpdateVariantPrice

        product_id = current_domain.process(
            CreateProduct(sku="PRICE-001", title="Price Test"),
            asynchronous=False,
        )

        current_domain.process(
            AddVariant(
                product_id=product_id,
                variant_sku="PRICE-VAR-001",
                attributes='{"size": "S"}',
                base_price=10.00,
                currency="USD",
            ),
            asynchronous=False,
        )

        # Get the variant ID from the persisted product
        from catalogue.product.product import Product

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = str(product.variants[0].id)

        current_domain.process(
            UpdateVariantPrice(
                product_id=product_id,
                variant_id=variant_id,
                base_price=15.00,
            ),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        price_events = [r for r in records if r.type == "Catalogue.VariantPriceChanged.v1"]
        assert len(price_events) == 1
        assert price_events[0].data["previous_price"] == 10.0
        assert price_events[0].data["new_price"] == 15.0


# ---------------------------------------------------------------------------
# Outbox stream isolation
# ---------------------------------------------------------------------------
class TestOutboxStreamIsolation:
    """Verify that events from different aggregates use distinct streams."""

    def test_identity_events_use_customer_stream(self, identity_ctx):
        """All identity events use the identity::customer-<id> stream."""
        from identity.customer.registration import RegisterCustomer

        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-STREAM-001",
                email="stream@example.com",
                first_name="Stream",
                last_name="Test",
            ),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        for record in records:
            assert record.stream_name.startswith("identity::customer-")
            assert customer_id in record.stream_name

    def test_catalogue_product_and_category_streams_differ(self, catalogue_ctx):
        """Product and Category events land in distinct stream categories."""
        from catalogue.category.management import CreateCategory
        from catalogue.product.creation import CreateProduct

        current_domain.process(
            CreateProduct(sku="STREAM-PROD-001", title="Stream Product"),
            asynchronous=False,
        )

        current_domain.process(
            CreateCategory(name="Stream Category"),
            asynchronous=False,
        )

        outbox_repo = current_domain._get_outbox_repo("default")
        records = outbox_repo.find_unprocessed()

        product_streams = {r.stream_name for r in records if "product" in r.stream_name}
        category_streams = {r.stream_name for r in records if "category" in r.stream_name}

        assert len(product_streams) >= 1
        assert len(category_streams) >= 1
        assert product_streams.isdisjoint(category_streams)
