"""Token budget allocation engine for smart context packing (Phase 8)."""

import json
from dataclasses import dataclass, field
from typing import Any

from barsa.context.models import CompletenessStatus, RankingExplanation, TokenUsageMetadata
from barsa.context.token_counter import TokenCounter


@dataclass
class AllocationResult:
    """Result of budget allocation pass."""

    included_mandatory: list[dict[str, Any]]
    included_optional: list[dict[str, Any]]
    omitted_record_refs: list[str]
    token_usage: TokenUsageMetadata
    completeness: CompletenessStatus
    completeness_reasons: list[str] = field(default_factory=list)


class TokenBudgetAllocator:
    """Enforces strict token limits while prioritizing mandatory records over optional records."""

    def __init__(self, token_counter: TokenCounter) -> None:
        self.counter = token_counter

    def allocate(
        self,
        max_tokens: int,
        reserved_overhead: int,
        mandatory_records: list[dict[str, Any]],
        candidate_optional: list[tuple[dict[str, Any], RankingExplanation]],
    ) -> AllocationResult:
        """Pack records into the available budget deterministically."""
        available_budget = max(10, max_tokens - reserved_overhead)
        reasons: list[str] = []
        omitted_refs: list[str] = []

        # Step 1: Measure mandatory records
        mandatory_json = json.dumps(mandatory_records, ensure_ascii=False)
        mandatory_tokens = self.counter.count(mandatory_json)

        # Base framing tokens (JSON wrapper overhead)
        framing_tokens = max(10, int(mandatory_tokens * 0.05))
        total_used = mandatory_tokens + framing_tokens

        # Check if mandatory records exceed total budget
        if total_used > available_budget:
            # Insufficient budget!
            for rec, _exp in candidate_optional:
                r_id = str(rec.get("id") or rec.get("raw_id") or "")
                if r_id:
                    omitted_refs.append(r_id)

            reasons.append(
                f"Mandatory Level 1 essential context ({mandatory_tokens} tokens) exceeds "
                f"available budget ({available_budget} tokens). Budget is insufficient."
            )
            usage = TokenUsageMetadata(
                count=total_used,
                budget=max_tokens,
                method=self.counter.estimation_method,
                tokenizer=self.counter.name,
                reserved_margin=reserved_overhead,
                utilization_percent=round((total_used / max_tokens) * 100, 1),
            )
            return AllocationResult(
                included_mandatory=mandatory_records,
                included_optional=[],
                omitted_record_refs=omitted_refs,
                token_usage=usage,
                completeness=CompletenessStatus.INSUFFICIENT,
                completeness_reasons=reasons,
            )

        # Step 2: Sort candidate optional records by algorithmic score descending
        sorted_candidates = sorted(candidate_optional, key=lambda x: x[1].relevance_score, reverse=True)

        included_optional: list[dict[str, Any]] = []
        any_optional_omitted = False

        for rec, _exp in sorted_candidates:
            rec_id = str(rec.get("id") or rec.get("raw_id") or "")
            rec_tokens = self.counter.count(json.dumps(rec, ensure_ascii=False))

            if total_used + rec_tokens <= available_budget:
                included_optional.append(rec)
                total_used += rec_tokens
            else:
                any_optional_omitted = True
                if rec_id:
                    omitted_refs.append(rec_id)

        completeness = CompletenessStatus.SUFFICIENT
        if any_optional_omitted:
            completeness = CompletenessStatus.PARTIAL
            reasons.append(
                f"Omitted {len(omitted_refs)} lower-ranked optional record(s) to strictly fit within token budget."
            )
        else:
            reasons.append("All requested and relevant project context comfortably fits within token budget.")

        usage = TokenUsageMetadata(
            count=total_used,
            budget=max_tokens,
            method=self.counter.estimation_method,
            tokenizer=self.counter.name,
            reserved_margin=reserved_overhead,
            utilization_percent=round((total_used / max_tokens) * 100, 1),
        )

        return AllocationResult(
            included_mandatory=mandatory_records,
            included_optional=included_optional,
            omitted_record_refs=omitted_refs,
            token_usage=usage,
            completeness=completeness,
            completeness_reasons=reasons,
        )
