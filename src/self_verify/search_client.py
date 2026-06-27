"""Search abstraction — pluggable search backends."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str
    source: str = "web"


@dataclass
class ClaimSearchResults:
    """All search results for a single claim across 3 angles."""

    claim_text: str
    evidence_results: list[SearchResult] = field(default_factory=list)
    neutral_results: list[SearchResult] = field(default_factory=list)
    antithesis_results: list[SearchResult] = field(default_factory=list)

    @property
    def total_results(self) -> int:
        return (
            len(self.evidence_results)
            + len(self.neutral_results)
            + len(self.antithesis_results)
        )

    @property
    def supports_claim(self) -> bool:
        """Heuristic: claim is supported if evidence search returns results
        and antithesis doesn't strongly contradict."""
        has_evidence = len(self.evidence_results) > 0
        strong_contradiction = len(self.antithesis_results) >= 3
        return has_evidence and not strong_contradiction

    @property
    def contradicts_claim(self) -> bool:
        """Heuristic: claim is contradicted if neutral or antithesis
        returns strong counter-evidence."""
        return len(self.antithesis_results) >= 3 and len(self.evidence_results) == 0

    @property
    def uncertain(self) -> bool:
        """No clear signal either way."""
        return not self.supports_claim and not self.contradicts_claim

    @property
    def supporting_sources(self) -> list[SearchResult]:
        """Sources that support the claim."""
        return self.evidence_results[:3]

    @property
    def contradicting_sources(self) -> list[SearchResult]:
        """Sources that contradict the claim."""
        return self.antithesis_results[:3]


class SearchClient:
    """Abstract search interface.

    Default implementation uses DuckDuckGo via the `ddgs` CLI.
    Subclass to add other providers (SerpAPI, Bing, custom).
    """

    def __init__(self, provider: str = "duckduckgo", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search the web and return results."""
        if self.provider == "duckduckgo":
            return self._search_ddg(query, max_results)
        elif self.provider == "none":
            return []
        else:
            raise ValueError(f"Unknown search provider: {self.provider}")

    def _search_ddg(self, query: str, max_results: int) -> list[SearchResult]:
        """Search via DuckDuckGo using the ddgs library or CLI."""
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
                return [
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", "")[:300],
                        source="duckduckgo",
                    )
                    for r in raw
                ]
        except ImportError:
            # Fallback: try CLI
            import subprocess
            import json

            try:
                result = subprocess.run(
                    ["ddgs", "text", "-k", query, "-m", str(max_results), "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    return [
                        SearchResult(
                            title=r.get("title", ""),
                            url=r.get("href", ""),
                            snippet=r.get("body", "")[:300],
                            source="duckduckgo",
                        )
                        for r in data
                    ]
            except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
                pass
            return []
        except Exception:
            return []
