import math
from typing import Any

from app.schemas.common import Explanation
from app.schemas.education import SharedEducationResponse, SharedEducationResult
from app.schemas.entities import EntitySummary


class EducationService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def get_shared_education(self, source_id: str, target_id: str) -> SharedEducationResponse:
        rows = self.repository.shared_education_rows(source_id=source_id, target_id=target_id)
        results = [self._result_from_row(row) for row in rows]
        results = sorted(
            results,
            key=lambda item: (-item.score, -item.attendance_overlap_years, item.institution.display_name),
        )
        return SharedEducationResponse(source_id=source_id, target_id=target_id, count=len(results), institutions=results)

    def _result_from_row(self, row: dict[str, Any]) -> SharedEducationResult:
        overlap_years = self._overlap_years(
            row.get("source_start_year"),
            row.get("source_end_year"),
            row.get("target_start_year"),
            row.get("target_end_year"),
        )
        field_match = self._same_text(row.get("source_field"), row.get("target_field"))
        degree_match = self._same_text(row.get("source_degree"), row.get("target_degree"))
        probability = self._co_attendance_probability(overlap_years, field_match, degree_match)
        source_overlap_score = float(row.get("source_overlap_score") or 0.0)
        target_overlap_score = float(row.get("target_overlap_score") or 0.0)
        source_confidence = (source_overlap_score + target_overlap_score) / 2
        score = min(1.0, probability * 0.75 + source_confidence * 0.25)

        institution = EntitySummary(
            id=row["institution_id"],
            label=row["institution_label"],
            display_name=row["institution_display_name"],
            properties=dict(row["institution_properties"] or {}),
        )
        explanation = Explanation(
            summary=(
                f"Both people studied at {institution.display_name}"
                + (f" with {overlap_years} overlapping attendance year(s)." if overlap_years else " without an overlapping attendance window.")
            ),
            algorithms=["education_common_neighbor", "attendance_year_overlap", "degree_field_similarity", "co_attendance_probability"],
            evidence=[
                {
                    "type": "shared_education",
                    "institution_id": institution.id,
                    "attendance_overlap_years": overlap_years,
                    "field_of_study_match": field_match,
                    "degree_level_match": degree_match,
                }
            ],
        )
        return SharedEducationResult(
            institution=institution,
            source_degree=row.get("source_degree"),
            target_degree=row.get("target_degree"),
            source_field=row.get("source_field"),
            target_field=row.get("target_field"),
            source_start_year=self._int_or_none(row.get("source_start_year")),
            source_end_year=self._int_or_none(row.get("source_end_year")),
            target_start_year=self._int_or_none(row.get("target_start_year")),
            target_end_year=self._int_or_none(row.get("target_end_year")),
            attendance_overlap_years=overlap_years,
            field_of_study_match=field_match,
            degree_level_match=degree_match,
            co_attendance_probability=round(probability, 6),
            score=round(score, 6),
            explanation=explanation,
        )

    @classmethod
    def _overlap_years(
        cls,
        source_start: int | str | None,
        source_end: int | str | None,
        target_start: int | str | None,
        target_end: int | str | None,
    ) -> int:
        start_a = cls._int_or_none(source_start)
        end_a = cls._int_or_none(source_end)
        start_b = cls._int_or_none(target_start)
        end_b = cls._int_or_none(target_end)
        if start_a is None or end_a is None or start_b is None or end_b is None:
            return 0
        return max(0, min(end_a, end_b) - max(start_a, start_b))

    @staticmethod
    def _same_text(source: str | None, target: str | None) -> bool:
        if source is None or target is None:
            return False
        return source.strip().casefold() == target.strip().casefold()

    @staticmethod
    def _co_attendance_probability(overlap_years: int, field_match: bool, degree_match: bool) -> float:
        if overlap_years <= 0:
            return 0.0
        field_weight = 1.5 if field_match else 1.0
        degree_weight = 1.2 if degree_match else 1.0
        signal = overlap_years * field_weight * degree_weight
        return 1 / (1 + math.exp(-signal))

    @staticmethod
    def _int_or_none(value: int | str | None) -> int | None:
        if value is None:
            return None
        return int(value)
