"""Domain initialization and configuration."""

from protean.domain import Domain

from catalogue.utils.logging import configure_logging, get_logger
from shared.enrichment import enrich_command, enrich_event

# Configure logging for the application
configure_logging(level="INFO", log_dir="logs", log_file_prefix="shopstream")

# Get logger for this module
logger = get_logger(__name__)

# Domain Composition Root
catalogue = Domain(name="catalogue")

# Message enrichment — adds request context (request_id, user_id) to all messages
catalogue.register_command_enricher(enrich_command)
catalogue.register_event_enricher(enrich_event)
