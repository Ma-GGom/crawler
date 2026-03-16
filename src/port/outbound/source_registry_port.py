from abc import ABC, abstractmethod

from domain.model.source_registry import SourceCrawlResult, SourceRegistrySeed


class SourceRegistryPort(ABC):
    @abstractmethod
    def upsert_sources(self, sources: list[SourceRegistrySeed]) -> int:
        """Register source catalog rows for discovery and health tracking."""

    @abstractmethod
    def record_crawl_result(self, result: SourceCrawlResult) -> None:
        """Store last crawl status and counters for a source."""
