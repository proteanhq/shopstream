"""Domain initialization and configuration."""

from protean.domain import Domain

from catalogue.utils.logging import configure_logging, get_logger

# Configure logging for the application
configure_logging(level="INFO", log_dir="logs", log_file_prefix="shopstream")

# Get logger for this module
logger = get_logger(__name__)

# Domain Composition Root
catalogue = Domain(name="catalogue")
