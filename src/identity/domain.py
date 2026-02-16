"""Domain initialization and configuration."""

from protean.domain import Domain

from identity.utils.logging import configure_logging, get_logger

# Configure logging for the application
configure_logging()

# Get logger for this module
logger = get_logger(__name__)

# Domain Composition Root
identity = Domain(name="identity")
