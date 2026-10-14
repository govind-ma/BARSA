"""Barsa Smart Context Engine (SCE) — Public API (Phase 8)."""

from barsa.context.budget import TokenBudgetAllocator
from barsa.context.compression import (
    compress_checkpoint_record,
    compress_decision_record,
    compress_generic_record,
    compress_task_record,
)
from barsa.context.deduplication import RecordDeduplicator
from barsa.context.engine import SmartContextEngine
from barsa.context.incremental import IncrementalSyncService
from barsa.context.models import (
    BarsaContextPackage,
    CompletenessStatus,
    ContextEstimateResponse,
    ContextLevel,
    ContextRequest,
    ContextStatusResponse,
    IncrementalSyncMetadata,
    RankingExplanation,
    TokenUsageMetadata,
)
from barsa.context.ranking import RankingWeights, RelevanceRanker
from barsa.context.token_counter import (
    HeuristicTokenCounter,
    TiktokenTokenCounter,
    TokenCounter,
    get_token_counter,
)
from barsa.context.validation import ContextCompletenessValidator

__all__ = [
    "BarsaContextPackage",
    "CompletenessStatus",
    "ContextCompletenessValidator",
    "ContextEstimateResponse",
    "ContextLevel",
    "ContextRequest",
    "ContextStatusResponse",
    "HeuristicTokenCounter",
    "IncrementalSyncMetadata",
    "IncrementalSyncService",
    "RankingExplanation",
    "RankingWeights",
    "RecordDeduplicator",
    "RelevanceRanker",
    "SmartContextEngine",
    "TiktokenTokenCounter",
    "TokenBudgetAllocator",
    "TokenCounter",
    "TokenUsageMetadata",
    "compress_checkpoint_record",
    "compress_decision_record",
    "compress_generic_record",
    "compress_task_record",
    "get_token_counter",
]
