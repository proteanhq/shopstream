"""Mixed cross-domain workload scenario.

Combines all Identity and Catalogue journeys with weights that
model realistic e-commerce traffic patterns. This is the recommended
scenario for load baseline testing.
"""

from locust import HttpUser, between

from loadtests.scenarios.catalogue import (
    CategoryHierarchyBuilder,
    ProductCatalogBuilder,
    ProductLifecycleJourney,
)
from loadtests.scenarios.identity import (
    AccountLifecycleJourney,
    NewCustomerJourney,
    TierProgressionJourney,
)


class MixedWorkloadUser(HttpUser):
    """Realistic mixed workload simulating concurrent e-commerce activity.

    Weight distribution models real-world patterns:
    - Customer registration: most common write operation
    - Product catalog building: frequent seller activity
    - Account lifecycle: less frequent
    - Tier progression: occasional
    - Product lifecycle: occasional
    - Category management: least frequent (admin activity)

    Creates cross-domain pressure on both PostgreSQL databases
    simultaneously, testing the DomainContextMiddleware's ability
    to route to the correct domain under load.
    """

    wait_time = between(0.5, 3.0)
    tasks = {
        NewCustomerJourney: 10,  # 33% — most common
        ProductCatalogBuilder: 8,  # 27% — frequent seller activity
        AccountLifecycleJourney: 4,  # 13%
        TierProgressionJourney: 3,  # 10%
        ProductLifecycleJourney: 3,  # 10%
        CategoryHierarchyBuilder: 2,  #  7% — least common (admin)
    }
