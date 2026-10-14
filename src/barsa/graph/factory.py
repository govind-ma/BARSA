import logging

from barsa.core.config import Settings
from barsa.graph.falkordb import FalkorDBGraphProvider
from barsa.graph.memory import InMemoryGraphProvider
from barsa.graph.protocol import GraphProvider

logger = logging.getLogger("barsa.graph.factory")

# Internal registry/cache mapping settings or mode to GraphProvider

_GRAPH_INSTANCES: dict[str, GraphProvider] = {}


def reset_graph_instances() -> None:
    """Clear cached GraphProvider instances. Useful in test fixtures."""
    _GRAPH_INSTANCES.clear()


def get_graph_provider(settings: Settings) -> GraphProvider:
    """Create or return the appropriate GraphProvider based on settings and connectivity."""
    cache_key = f"{settings.db_path}:{settings.graph_enabled}:{settings.falkordb_host}:{settings.falkordb_port}:{settings.falkordb_graph_prefix}"
    if cache_key in _GRAPH_INSTANCES:
        return _GRAPH_INSTANCES[cache_key]

    if settings.graph_enabled:
        falkor_provider = FalkorDBGraphProvider(settings)
        if falkor_provider.is_available():
            logger.info(
                "Using FalkorDBGraphProvider connected to %s:%s", settings.falkordb_host, settings.falkordb_port
            )
            _GRAPH_INSTANCES[cache_key] = falkor_provider
            return falkor_provider
        logger.warning(
            "FalkorDB is enabled but unavailable at %s:%s. Falling back to InMemoryGraphProvider.",
            settings.falkordb_host,
            settings.falkordb_port,
        )

    provider = InMemoryGraphProvider()
    _GRAPH_INSTANCES[cache_key] = provider
    return provider
