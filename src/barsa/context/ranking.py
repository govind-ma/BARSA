"""Deterministic relevance ranking engine with explainable metadata."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from barsa.context.models import RankingExplanation


@dataclass
class RankingWeights:
    """Configurable weights for deterministic record ranking."""

    task_match: float = 0.30  # Record directly attached to target task
    approved_decision: float = 0.25  # Approved architectural decision status
    graph_proximity: float = 0.20  # 1-hop or direct dependency in knowledge graph
    query_similarity: float = 0.15  # Keyword overlap with user query
    verification_status: float = 0.08  # Verified record (e.g. is_verified == True)
    recency: float = 0.02  # Timestamp recency factor (deliberately low to avoid unverified recency bias)


class RelevanceRanker:
    """Calculates deterministic algorithmic relevance scores for candidate memory records."""

    def __init__(self, weights: RankingWeights | None = None) -> None:
        self.weights = weights or RankingWeights()

    def rank_record(
        self,
        record: dict[str, Any],
        target_task_id: str | None = None,
        query: str | None = None,
        graph_distance: int | None = None,  # 0 = self, 1 = direct neighbor, 2 = 2-hop, None = disconnected
        is_dependency: bool = False,
        is_checkpoint_ref: bool = False,
    ) -> RankingExplanation:
        """Compute an algorithmic score in [0.0, 1.0] and detailed reasons."""
        reasons: list[str] = []
        score = 0.0

        r_id = str(record.get("id") or record.get("raw_id") or "unknown")
        r_type = str(record.get("record_type") or "unknown")

        # 1. Direct Task Match / Association
        rec_task_id = record.get("task_id") or record.get("target_task_id")
        if target_task_id and (r_id == target_task_id or rec_task_id == target_task_id):
            score += self.weights.task_match
            reasons.append("Directly associated with target task")
        elif is_dependency:
            score += self.weights.task_match * 0.8
            reasons.append("Direct dependency or blocker of target task")

        # 2. Approved Decision Priority
        status = str(record.get("status") or "").lower()
        if r_type == "decision":
            if status == "approved":
                score += self.weights.approved_decision
                reasons.append("Approved architectural decision")
            elif status == "proposed":
                score += self.weights.approved_decision * 0.4
                reasons.append("Proposed architectural decision (pending review)")
            elif status == "superseded":
                score += self.weights.approved_decision * 0.1
                reasons.append("Superseded historical decision")

        # 3. Graph Proximity
        if graph_distance is not None:
            if graph_distance <= 1:
                score += self.weights.graph_proximity
                reasons.append("Direct 1-hop neighbor in knowledge graph")
            elif graph_distance == 2:
                score += self.weights.graph_proximity * 0.6
                reasons.append("2-hop connected node in knowledge graph")
            elif graph_distance > 2:
                score += self.weights.graph_proximity * 0.2
                reasons.append(f"{graph_distance}-hop distant graph node")

        # 4. Checkpoint Reference Boost
        if is_checkpoint_ref:
            score += 0.10
            reasons.append("Explicitly referenced by latest resume checkpoint")

        # 5. Query Keyword Similarity
        if query:
            q_tokens = set(re.findall(r"\w+", query.lower()))
            if q_tokens:
                text_corpus = " ".join(
                    [
                        str(record.get("title") or ""),
                        str(record.get("name") or ""),
                        str(record.get("summary") or ""),
                        str(record.get("content") or ""),
                        str(record.get("rationale") or ""),
                    ]
                ).lower()
                rec_tokens = set(re.findall(r"\w+", text_corpus))
                overlap = q_tokens.intersection(rec_tokens)
                if overlap:
                    similarity_ratio = min(1.0, len(overlap) / max(1, len(q_tokens)))
                    query_score = self.weights.query_similarity * similarity_ratio
                    score += query_score
                    reasons.append(f"Query keyword overlap ({len(overlap)} match(es))")

        # 6. Verification Status
        # If record is an unverified claim, do NOT give verification bonus
        is_verified = record.get("is_verified")
        if is_verified is True or record.get("verification_status") == "verified":
            score += self.weights.verification_status
            reasons.append("Formally verified knowledge claim")
        elif is_verified is False:
            reasons.append("Unverified claim (no truth presumption)")

        # 7. Recency
        created_at_raw = record.get("created_at") or record.get("updated_at")
        if created_at_raw:
            try:
                if isinstance(created_at_raw, str):
                    ts = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                elif isinstance(created_at_raw, datetime):
                    ts = created_at_raw
                else:
                    ts = None

                if ts:
                    # Soft recency: within 30 days = full recency fraction
                    score += self.weights.recency
                    reasons.append("Recent modification timestamp")
            except Exception:
                pass

        # Clamp between 0.05 and 1.0 (baseline floor for existing valid project records)
        final_score = round(max(0.05, min(1.0, score)), 3)
        if not reasons:
            reasons.append("General project context candidate")

        return RankingExplanation(
            record_id=r_id,
            record_type=r_type,
            relevance_score=final_score,
            reasons=reasons,
        )
