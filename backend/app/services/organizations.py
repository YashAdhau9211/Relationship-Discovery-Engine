from datetime import date, datetime
from typing import Any

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary
from app.schemas.organizations import SharedOrganizationResult, SharedOrganizationsResponse


class OrganizationService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def get_shared_organizations(self, source_id: str, target_id: str) -> SharedOrganizationsResponse:
        rows = self.repository.shared_organization_rows(source_id=source_id, target_id=target_id)
        results = [self._result_from_row(row) for row in rows]
        results = sorted(results, key=lambda item: (-item.score, -item.overlap_months, item.organization.display_name))
        return SharedOrganizationsResponse(source_id=source_id, target_id=target_id, count=len(results), organizations=results)

    def _result_from_row(self, row: dict[str, Any]) -> SharedOrganizationResult:
        overlap_months = self._overlap_months(
            row.get("source_start_date"),
            row.get("source_end_date"),
            row.get("target_start_date"),
            row.get("target_end_date"),
        )
        concurrent = overlap_months > 0
        org_importance_score = float(row.get("org_importance_score") or 0.0)
        score = org_importance_score if concurrent else org_importance_score * 0.5

        organization = EntitySummary(
            id=row["org_id"],
            label=row["org_label"],
            display_name=row["org_display_name"],
            properties=dict(row["org_properties"] or {}),
        )
        explanation = Explanation(
            summary=(
                f"{row.get('source_role') or 'Source person'} and {row.get('target_role') or 'target person'} "
                f"share {organization.display_name}"
                + (" with overlapping tenure." if concurrent else " without an overlapping tenure window.")
            ),
            algorithms=["bipartite_common_neighbor", "temporal_overlap", "organization_pagerank_weight"],
            evidence=[
                {
                    "type": "shared_organization",
                    "organization_id": organization.id,
                    "source_relationship_type": row["source_relationship_type"],
                    "target_relationship_type": row["target_relationship_type"],
                    "overlap_months": overlap_months,
                    "concurrent": concurrent,
                }
            ],
        )
        return SharedOrganizationResult(
            organization=organization,
            source_role=row.get("source_role"),
            target_role=row.get("target_role"),
            source_relationship_type=row["source_relationship_type"],
            target_relationship_type=row["target_relationship_type"],
            source_start_date=row.get("source_start_date"),
            source_end_date=row.get("source_end_date"),
            target_start_date=row.get("target_start_date"),
            target_end_date=row.get("target_end_date"),
            overlap_months=overlap_months,
            concurrent=concurrent,
            org_importance_score=round(org_importance_score, 6),
            score=round(score, 6),
            explanation=explanation,
        )

    @classmethod
    def _overlap_months(
        cls,
        source_start: str | None,
        source_end: str | None,
        target_start: str | None,
        target_end: str | None,
        reference_date: date | None = None,
    ) -> int:
        start_a = cls._parse_date(source_start)
        start_b = cls._parse_date(target_start)
        if start_a is None or start_b is None:
            return 0
        reference = reference_date or date.today()
        end_a = cls._parse_date(source_end) or reference
        end_b = cls._parse_date(target_end) or reference
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)
        if overlap_end < overlap_start:
            return 0
        return max(0, ((overlap_end.year - overlap_start.year) * 12) + (overlap_end.month - overlap_start.month))

    @staticmethod
    def _parse_date(value: str | date | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value)).date()
