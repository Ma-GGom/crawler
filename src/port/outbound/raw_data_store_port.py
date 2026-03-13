from abc import ABC, abstractmethod


class RawDataStorePort(ABC):
    @abstractmethod
    def save(
        self,
        *,
        source: str,
        payload: dict[str, object],
        parsed_status: str,
    ) -> None:
        """Persist raw crawled payload for auditing and replay."""

    def prune(
        self,
        *,
        parsed_status: str,
        older_than_days: int,
    ) -> int:
        """Delete old raw data rows by status; return deleted row count."""
        return 0
