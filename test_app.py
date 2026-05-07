"""Unit tests for app.py — pure logic only, no OpenAI calls required."""
import json
import pytest
from unittest.mock import MagicMock, patch

# Patch streamlit before importing app so the module loads cleanly in test context
import sys
sys.modules.setdefault("streamlit", MagicMock())

from app import (
    BAAssistant, CompanyInputs, PipelineResults, PDFGenerator, WordGenerator,
    _is_url, scrape_website,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def assistant():
    """BAAssistant with a dummy API key; LLM calls are never made in these tests."""
    with patch("openai.OpenAI"):
        return BAAssistant("sk-test-dummy")


@pytest.fixture
def sample_inputs():
    return CompanyInputs(
        linkedin_url="https://linkedin.com/company/acme",
        website="https://acme.io - We build AI-native logistics software",
        job_posting="Senior ML Engineer, 5+ years, PyTorch, Kubernetes required",
    )


@pytest.fixture
def pdf_gen():
    return PDFGenerator()


@pytest.fixture
def word_gen():
    return WordGenerator()


# ── CompanyInputs ─────────────────────────────────────────────────────────────

class TestCompanyInputs:
    def test_fields_stored(self, sample_inputs):
        assert sample_inputs.linkedin_url.startswith("https://linkedin.com")
        assert "logistics" in sample_inputs.website
        assert "ML Engineer" in sample_inputs.job_posting

    def test_empty_strings_allowed(self):
        ci = CompanyInputs("", "", "")
        assert ci.linkedin_url == ""


# ── PipelineResults ──────────────────────────────────────────────────────────

class TestPipelineResults:
    def test_construction(self):
        pr = PipelineResults(
            signals={"company_name": "Acme"},
            diagnosis="diagnosis text",
            hook="hook text",
            audit="audit text",
            close="close text",
        )
        assert pr.signals["company_name"] == "Acme"
        assert pr.hook == "hook text"


# ── BAAssistant._get_cache_key ────────────────────────────────────────────────

class TestCacheKey:
    def test_same_inputs_same_key(self, assistant, sample_inputs):
        k1 = assistant._get_cache_key(sample_inputs)
        k2 = assistant._get_cache_key(sample_inputs)
        assert k1 == k2

    def test_different_inputs_different_key(self, assistant, sample_inputs):
        other = CompanyInputs("a", "b", "c")
        assert assistant._get_cache_key(sample_inputs) != assistant._get_cache_key(other)

    def test_key_is_hex_string(self, assistant, sample_inputs):
        key = assistant._get_cache_key(sample_inputs)
        assert len(key) == 32
        int(key, 16)  # raises ValueError if not hex


# ── BAAssistant._extract_json ─────────────────────────────────────────────────

class TestExtractJson:
    def test_plain_json(self, assistant):
        raw = '{"company_name": "Acme", "industry": "logistics"}'
        result = assistant._extract_json(raw)
        assert result["company_name"] == "Acme"

    def test_json_with_code_fence(self, assistant):
        raw = '```json\n{"company_name": "Acme"}\n```'
        result = assistant._extract_json(raw)
        assert result["company_name"] == "Acme"

    def test_json_with_unlabelled_fence(self, assistant):
        raw = '```\n{"company_name": "Acme"}\n```'
        result = assistant._extract_json(raw)
        assert result["company_name"] == "Acme"

    def test_invalid_json_raises(self, assistant):
        with pytest.raises(json.JSONDecodeError):
            assistant._extract_json("not json at all")


# ── BAAssistant._get_default_prompts ─────────────────────────────────────────

class TestDefaultPrompts:
    REQUIRED_KEYS = {"extract_signals", "diagnose", "generate_hook", "generate_audit", "generate_close"}

    def test_all_keys_present(self, assistant):
        prompts = assistant._get_default_prompts()
        assert self.REQUIRED_KEYS <= prompts.keys()

    def test_prompts_are_non_empty_strings(self, assistant):
        for key, val in assistant._get_default_prompts().items():
            assert isinstance(val, str) and len(val) > 0, f"Prompt '{key}' is empty"


# ── PDFGenerator._clean_text ─────────────────────────────────────────────────

class TestPDFCleanText:
    def test_strips_markdown_headers(self, pdf_gen):
        result = pdf_gen._clean_text("# Title\nSome text")
        assert "#" not in result
        assert "Title" in result

    def test_replaces_smart_quotes(self, pdf_gen):
        result = pdf_gen._clean_text("“Hello”")
        assert '"Hello"' in result

    def test_replaces_em_dash(self, pdf_gen):
        result = pdf_gen._clean_text("before—after")
        assert "-" in result
        assert "—" not in result

    def test_ascii_only_output(self, pdf_gen):
        result = pdf_gen._clean_text("café naïve")
        assert all(ord(c) < 128 for c in result)

    def test_empty_string(self, pdf_gen):
        assert pdf_gen._clean_text("") == ""


# ── WordGenerator._clean_text_for_word ───────────────────────────────────────

class TestWordCleanText:
    def test_strips_markdown(self, word_gen):
        result = word_gen._clean_text_for_word("## Heading\nParagraph text")
        assert "##" not in result
        assert "Heading" in result

    def test_collapses_blank_lines(self, word_gen):
        result = word_gen._clean_text_for_word("a\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_empty_string(self, word_gen):
        assert word_gen._clean_text_for_word("") == ""


# ── _is_url ───────────────────────────────────────────────────────────────────

class TestIsUrl:
    def test_http_url(self):
        assert _is_url("http://example.com") is True

    def test_https_url(self):
        assert _is_url("https://acme.io") is True

    def test_url_with_path(self):
        assert _is_url("https://acme.io/about?ref=1") is True

    def test_plain_text_is_not_url(self):
        assert _is_url("Acme is a logistics company") is False

    def test_ftp_is_not_url(self):
        assert _is_url("ftp://files.example.com") is False

    def test_empty_string(self):
        assert _is_url("") is False

    def test_partial_url_no_netloc(self):
        assert _is_url("https://") is False


# ── scrape_website ─────────────────────────────────────────────────────────────

class TestScrapeWebsite:
    HTML = "<html><body><h1>Acme</h1><p>We build logistics software.</p></body></html>"

    def _mock_response(self, text, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.text = text
        resp.raise_for_status = MagicMock()
        return resp

    def test_returns_markdown_on_success(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value = self._mock_response(self.HTML)
            ok, content = scrape_website("https://acme.io")
        assert ok is True
        assert "Acme" in content
        assert "logistics" in content

    def test_strips_script_tags(self):
        html = "<html><body><p>Real content</p><script>evil()</script></body></html>"
        with patch("requests.get") as mock_get:
            mock_get.return_value = self._mock_response(html)
            ok, content = scrape_website("https://acme.io")
        assert ok is True
        assert "evil" not in content
        assert "Real content" in content

    def test_timeout_returns_false(self):
        import requests as req
        with patch("requests.get", side_effect=req.exceptions.Timeout):
            ok, msg = scrape_website("https://acme.io")
        assert ok is False
        assert "timed out" in msg.lower()

    def test_connection_error_returns_false(self):
        import requests as req
        with patch("requests.get", side_effect=req.exceptions.ConnectionError):
            ok, msg = scrape_website("https://acme.io")
        assert ok is False
        assert "connect" in msg.lower()

    def test_http_error_returns_false(self):
        import requests as req
        resp = MagicMock()
        resp.status_code = 404
        with patch("requests.get") as mock_get:
            mock_get.return_value = self._mock_response("", status=404)
            mock_get.return_value.raise_for_status.side_effect = req.exceptions.HTTPError(response=resp)
            ok, msg = scrape_website("https://acme.io")
        assert ok is False
        assert "404" in msg

    def test_truncates_long_content(self):
        long_html = f"<html><body><p>{'x' * 50_000}</p></body></html>"
        with patch("requests.get") as mock_get:
            mock_get.return_value = self._mock_response(long_html)
            ok, content = scrape_website("https://acme.io")
        assert ok is True
        assert len(content) <= 40_100  # max_chars + truncation message


# ── CompanyInputs.website_context ────────────────────────────────────────────

class TestWebsiteContext:
    def test_returns_scraped_content_when_present(self):
        ci = CompanyInputs("url", "https://acme.io", "job", website_content="# Acme\nWe build things.")
        assert ci.website_context == "# Acme\nWe build things."

    def test_falls_back_to_website_field_when_no_content(self):
        ci = CompanyInputs("url", "some free-text summary", "job")
        assert ci.website_context == "some free-text summary"

    def test_falls_back_when_content_is_none(self):
        ci = CompanyInputs("url", "https://acme.io", "job", website_content=None)
        assert ci.website_context == "https://acme.io"
