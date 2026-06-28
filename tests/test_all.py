"""Tests for self-verify-pipelines."""

from findout.config import Config, LLMConfig
from findout.search_client import SearchResult, ClaimSearchResults, SearchClient
from findout.gate import Gate


class TestConfig:
    def test_default_config(self):
        c = Config()
        assert c.llm.model == "", "default model should be empty — caller must provide it"
        assert c.pipeline.default_variant == "base"

    def test_explicit_config(self):
        c = Config(llm=LLMConfig(model="test-model", base_url="http://test:8000/v1"))
        assert c.llm.model == "test-model"
        assert c.llm.base_url == "http://test:8000/v1"


class TestSearchClient:
    def test_search_result_dataclass(self):
        r = SearchResult(title="Test", url="https://example.com", snippet="test snippet")
        assert r.title == "Test"
        assert r.url == "https://example.com"

    def test_claim_search_results(self):
        csr = ClaimSearchResults(claim_text="test claim")
        assert csr.uncertain is True
        assert csr.total_results == 0

    def test_claim_search_supported(self):
        csr = ClaimSearchResults(claim_text="test")
        csr.evidence_results.append(
            SearchResult(title="E", url="https://e.com", snippet="evidence")
        )
        assert csr.supports_claim is True
        assert csr.uncertain is False

    def test_claim_search_contradicted(self):
        csr = ClaimSearchResults(claim_text="test")
        csr.antithesis_results.extend([
            SearchResult(title="A1", url="https://a1.com", snippet="a1"),
            SearchResult(title="A2", url="https://a2.com", snippet="a2"),
            SearchResult(title="A3", url="https://a3.com", snippet="a3"),
        ])
        assert csr.contradicts_claim is True

    def test_search_client_no_provider(self):
        sc = SearchClient(provider="none")
        results = sc.search("test query")
        assert results == []


class TestGate:
    def test_gate_disabled(self):
        from findout.config import GateConfig
        gc = GateConfig(enabled=False)
        llm = LLMConfig()
        g = Gate(config=gc, llm_config=llm)
        assert g.classify("anything") == "visionary"

    def test_gate_classify_with_reason_disabled(self):
        from findout.config import GateConfig
        gc = GateConfig(enabled=False)
        llm = LLMConfig()
        g = Gate(config=gc, llm_config=llm)
        decision, reason = g.classify_with_reason("anything")
        assert decision == "visionary"


class TestPipeline:
    def test_pipeline_result_counts(self):
        from findout.result import PipelineResult
        r = PipelineResult(
            query="test",
            answer="test answer",
            pipeline_variant="base",
            total_claims=3,
            verified_claims=1,
            contradicted_claims=1,
            uncertain_claims=1,
        )
        assert r.unverified_claims == []
        assert r.pipeline_variant == "base"
