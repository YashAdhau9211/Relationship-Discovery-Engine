from typing import Any

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary
from app.schemas.interactions import CommonInteractionsResponse, DirectInteraction, SharedInteractionTarget


class InteractionService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def get_common_interactions(self, source_id: str, target_id: str) -> CommonInteractionsResponse:
        direct_rows = self.repository.direct_interaction_rows(source_id=source_id, target_id=target_id)
        shared_rows = self.repository.shared_target_rows(source_id=source_id, target_id=target_id)
        direct_interactions = [self._direct_from_row(row) for row in direct_rows]
        shared_targets = [self._shared_target_from_row(row) for row in shared_rows]
        shared_targets = sorted(
            shared_targets,
            key=lambda item: (-item.resource_allocation_contribution, -item.recency_score, item.target.display_name),
        )

        direct_interaction_count = sum(item.count for item in direct_interactions)
        resource_allocation_score = sum(item.resource_allocation_contribution for item in shared_targets)
        recency_score = self._combined_recency_score(direct_interactions, shared_targets)
        composite_score = self._composite_score(direct_interaction_count, len(shared_targets), resource_allocation_score, recency_score)

        explanation = Explanation(
            summary=(
                f"{source_id} and {target_id} have direct interaction evidence and shared interaction targets."
                if direct_interaction_count and shared_targets
                else f"{source_id} and {target_id} share common interaction targets."
                if shared_targets
                else f"{source_id} and {target_id} have direct interaction evidence."
                if direct_interaction_count
                else f"{source_id} and {target_id} have no common interaction evidence in the current graph."
            ),
            algorithms=[
                "direct_interaction_count",
                "common_interaction_targets",
                "resource_allocation_index",
                "recency_weighted_interaction_score",
            ],
            evidence=[
                {
                    "type": "common_interactions_summary",
                    "direct_interaction_count": direct_interaction_count,
                    "shared_target_count": len(shared_targets),
                    "resource_allocation_score": round(resource_allocation_score, 6),
                    "recency_score": round(recency_score, 6),
                }
            ],
        )
        return CommonInteractionsResponse(
            source_id=source_id,
            target_id=target_id,
            direct_interaction_count=direct_interaction_count,
            shared_target_count=len(shared_targets),
            resource_allocation_score=round(resource_allocation_score, 6),
            recency_score=round(recency_score, 6),
            composite_score=round(composite_score, 6),
            direct_interactions=direct_interactions,
            shared_targets=shared_targets,
            explanation=explanation,
        )

    def _direct_from_row(self, row: dict[str, Any]) -> DirectInteraction:
        return DirectInteraction(
            source_id=row["source_id"],
            target_id=row["target_id"],
            relationship_type=row["relationship_type"],
            interaction_type=row.get("interaction_type"),
            count=int(row.get("count") or 0),
            platform=row.get("platform"),
            recency_score=round(float(row.get("recency_score") or 0.0), 6),
            timestamps=list(row.get("timestamps") or []),
            properties=dict(row.get("properties") or {}),
        )

    def _shared_target_from_row(self, row: dict[str, Any]) -> SharedInteractionTarget:
        total_interactors = int(row.get("target_total_interactors") or 0)
        contribution = self._resource_allocation_contribution(total_interactors)
        recency_score = self._average([float(value or 0.0) for value in row.get("recency_scores", [])])
        return SharedInteractionTarget(
            target=EntitySummary(
                id=row["target_id"],
                label=row["target_label"],
                display_name=row["target_display_name"],
                properties=dict(row["target_properties"] or {}),
            ),
            source_interaction_count=int(row.get("source_interaction_count") or 0),
            target_interaction_count=int(row.get("target_interaction_count") or 0),
            target_total_interactors=total_interactors,
            resource_allocation_contribution=round(contribution, 6),
            interaction_types=self._unique_strings(row.get("interaction_types", [])),
            recency_score=round(recency_score, 6),
            relationship_types=self._unique_strings(row.get("relationship_types", [])),
        )

    @staticmethod
    def _resource_allocation_contribution(target_total_interactors: int) -> float:
        if target_total_interactors <= 0:
            return 0.0
        return 1 / target_total_interactors

    @classmethod
    def _composite_score(cls, direct_interaction_count: int, shared_target_count: int, resource_allocation_score: float, recency_score: float) -> float:
        direct_signal = min(1.0, direct_interaction_count / 10)
        shared_signal = min(1.0, shared_target_count / 5)
        ra_signal = min(1.0, resource_allocation_score)
        return min(1.0, direct_signal * 0.35 + shared_signal * 0.2 + ra_signal * 0.25 + recency_score * 0.2)

    @staticmethod
    def _combined_recency_score(direct_interactions: list[DirectInteraction], shared_targets: list[SharedInteractionTarget]) -> float:
        recencies = [item.recency_score for item in direct_interactions] + [item.recency_score for item in shared_targets]
        return InteractionService._average(recencies)

    @staticmethod
    def _average(values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def _unique_strings(values: list[Any]) -> list[str]:
        unique = {str(value) for value in values if value is not None}
        return sorted(unique)
