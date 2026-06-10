from datetime import datetime, timezone
from typing import Any

from app.schemas.common import Explanation
from app.schemas.entities import EntitySummary
from app.schemas.locations import SharedLocationResult, SharedLocationsResponse


class LocationService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def get_shared_locations(self, source_id: str, target_id: str) -> SharedLocationsResponse:
        rows = self.repository.shared_location_rows(source_id=source_id, target_id=target_id)
        results = [self._result_from_row(row) for row in rows]
        results = sorted(results, key=lambda item: (-item.score, -item.overlap_hours, item.location.display_name))
        return SharedLocationsResponse(source_id=source_id, target_id=target_id, count=len(results), locations=results)

    def _result_from_row(self, row: dict[str, Any]) -> SharedLocationResult:
        overlap_hours = self._overlap_hours(
            row.get("source_start_ts"),
            row.get("source_end_ts"),
            row.get("target_start_ts"),
            row.get("target_end_ts"),
        )
        source_frequency = int(row.get("source_frequency") or 0)
        target_frequency = int(row.get("target_frequency") or 0)
        combined_frequency = source_frequency + target_frequency
        source_recency = float(row.get("source_recency") or 0.0)
        target_recency = float(row.get("target_recency") or 0.0)
        spatial_distance_km = self._same_location_distance(row.get("latitude"), row.get("longitude"))
        co_presence_score = self._co_presence_score(overlap_hours, combined_frequency, source_recency, target_recency)
        score = co_presence_score

        location = EntitySummary(
            id=row["location_id"],
            label=row["location_label"],
            display_name=row["location_display_name"],
            properties=dict(row["location_properties"] or {}),
        )
        explanation = Explanation(
            summary=(
                f"Both people share {location.display_name}"
                + (f" with {overlap_hours:g} overlapping hour(s)." if overlap_hours else " without a bounded overlapping time window.")
            ),
            algorithms=["shared_location_common_neighbor", "temporal_overlap_hours", "spatial_proximity", "co_presence_score"],
            evidence=[
                {
                    "type": "shared_location",
                    "location_id": location.id,
                    "overlap_hours": overlap_hours,
                    "combined_frequency": combined_frequency,
                    "source_location_type": row.get("source_location_type"),
                    "target_location_type": row.get("target_location_type"),
                }
            ],
        )
        return SharedLocationResult(
            location=location,
            source_location_type=row.get("source_location_type"),
            target_location_type=row.get("target_location_type"),
            source_start_ts=row.get("source_start_ts"),
            source_end_ts=row.get("source_end_ts"),
            target_start_ts=row.get("target_start_ts"),
            target_end_ts=row.get("target_end_ts"),
            overlap_hours=round(overlap_hours, 6),
            spatial_distance_km=round(spatial_distance_km, 6),
            source_frequency=source_frequency,
            target_frequency=target_frequency,
            combined_frequency=combined_frequency,
            source_recency=round(source_recency, 6),
            target_recency=round(target_recency, 6),
            co_presence_score=round(co_presence_score, 6),
            score=round(score, 6),
            explanation=explanation,
        )

    @classmethod
    def _overlap_hours(
        cls,
        source_start: str | datetime | None,
        source_end: str | datetime | None,
        target_start: str | datetime | None,
        target_end: str | datetime | None,
    ) -> float:
        start_a = cls._parse_datetime(source_start)
        end_a = cls._parse_datetime(source_end)
        start_b = cls._parse_datetime(target_start)
        end_b = cls._parse_datetime(target_end)
        if start_a is None or start_b is None:
            return 0.0
        if end_a is None or end_b is None:
            if start_a == start_b:
                return 1.0
            return 0.0
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)
        if overlap_end <= overlap_start:
            return 0.0
        return (overlap_end - overlap_start).total_seconds() / 3600

    @staticmethod
    def _co_presence_score(overlap_hours: float, combined_frequency: int, source_recency: float, target_recency: float) -> float:
        overlap_signal = min(1.0, overlap_hours / 24)
        frequency_signal = min(1.0, combined_frequency / 10)
        recency_signal = (source_recency + target_recency) / 2
        return min(1.0, overlap_signal * 0.5 + frequency_signal * 0.3 + recency_signal * 0.2)

    @staticmethod
    def _same_location_distance(latitude: float | int | None, longitude: float | int | None) -> float:
        if latitude is None or longitude is None:
            return 0.0
        return 0.0

    @staticmethod
    def _parse_datetime(value: str | datetime | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
