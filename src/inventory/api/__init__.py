from inventory.api.routes import inventory_router, warehouse_router
from inventory.api.routes import maintenance_router as inventory_maintenance_router

__all__ = ["inventory_router", "warehouse_router", "inventory_maintenance_router"]
