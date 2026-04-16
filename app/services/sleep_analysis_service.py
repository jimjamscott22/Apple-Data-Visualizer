from __future__ import annotations


class SleepAnalysisService:
    def build_sleep_sessions(self, normalized_records: list[dict]) -> list[dict]:
        raise NotImplementedError(
            "Sleep session derivation is not implemented yet. The service boundary now exists "
            "for the MVP analytics pass."
        )
