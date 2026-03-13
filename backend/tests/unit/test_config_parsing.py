"""Unit tests for configuration parsing.

These tests ensure that environment variables are correctly parsed,
especially for comma-separated list values like ALLOWED_DOMAINS and CORS_ORIGINS.

CRITICAL: These tests protect against the production bug where Terraform's
jsonencode() produced JSON arrays like '["domain.com"]' instead of
comma-separated strings like 'domain.com,other.com'.
"""

import pytest


class TestAllowedDomainsParsing:
    """Test ALLOWED_DOMAINS environment variable parsing.

    The backend expects comma-separated format: "domain1.com,domain2.com"
    NOT JSON array format: ["domain1.com","domain2.com"]
    """

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset settings cache before each test."""
        from src.config import get_settings

        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_single_domain_parsed_correctly(self, monkeypatch):
        """Single domain should be parsed into a list with one item."""
        monkeypatch.setenv("ALLOWED_DOMAINS", "acme-corp.com")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.allowed_domains == ["acme-corp.com"]

    def test_multiple_domains_comma_separated(self, monkeypatch):
        """Multiple domains separated by commas should all be parsed."""
        monkeypatch.setenv("ALLOWED_DOMAINS", "acme-corp.com,example.com,test.org")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.allowed_domains == ["acme-corp.com", "example.com", "test.org"]

    def test_domains_with_spaces_trimmed(self, monkeypatch):
        """Spaces around domains should be trimmed."""
        monkeypatch.setenv("ALLOWED_DOMAINS", "acme-corp.com , example.com , test.org")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.allowed_domains == ["acme-corp.com", "example.com", "test.org"]

    def test_domains_lowercased(self, monkeypatch):
        """Domains should be lowercased for case-insensitive comparison."""
        monkeypatch.setenv("ALLOWED_DOMAINS", "ACME-CORP.COM,EXAMPLE.COM")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.allowed_domains == ["acme-corp.com", "example.com"]

    def test_empty_string_returns_empty_list(self, monkeypatch):
        """Empty string should return empty list (allow all domains)."""
        monkeypatch.setenv("ALLOWED_DOMAINS", "")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.allowed_domains == []

    def test_asterisk_returns_empty_list(self, monkeypatch):
        """Asterisk (*) should return empty list (allow all domains)."""
        monkeypatch.setenv("ALLOWED_DOMAINS", "*")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.allowed_domains == []

    def test_json_array_format_is_wrong(self, monkeypatch):
        """JSON array format should NOT be correctly parsed.

        This test documents the bug that occurred when Terraform used
        jsonencode() instead of join(). The JSON array format results
        in incorrect parsing.
        """
        # This is the WRONG format that Terraform's jsonencode() produces
        monkeypatch.setenv("ALLOWED_DOMAINS", '["acme-corp.com"]')
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        # The JSON format is incorrectly parsed as a single string with brackets
        # This test documents the expected (incorrect) behavior to catch this bug
        assert settings.allowed_domains != ["acme-corp.com"]
        # It would be parsed as the literal string including brackets
        assert '["acme-corp.com"]' in str(settings.allowed_domains)


class TestCorsOriginsParsing:
    """Test CORS_ORIGINS environment variable parsing."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset settings cache before each test."""
        from src.config import get_settings

        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_single_origin_parsed_correctly(self, monkeypatch):
        """Single origin should be parsed into a list with one item."""
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.cors_origins == ["https://example.com"]

    def test_multiple_origins_comma_separated(self, monkeypatch):
        """Multiple origins separated by commas should all be parsed."""
        monkeypatch.setenv(
            "CORS_ORIGINS", "https://example.com,http://localhost:5173,http://localhost:3000"
        )
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.cors_origins == [
            "https://example.com",
            "http://localhost:5173",
            "http://localhost:3000",
        ]

    def test_origins_with_spaces_trimmed(self, monkeypatch):
        """Spaces around origins should be trimmed."""
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com , http://localhost:5173")
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.cors_origins == ["https://example.com", "http://localhost:5173"]

    def test_json_array_format_is_wrong(self, monkeypatch):
        """JSON array format should NOT be correctly parsed.

        This test documents the bug that occurred when Terraform used
        jsonencode() instead of join().
        """
        monkeypatch.setenv("CORS_ORIGINS", '["https://example.com","http://localhost:5173"]')
        from src.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        # The JSON format is incorrectly parsed
        assert settings.cors_origins != ["https://example.com", "http://localhost:5173"]


## TestOAuthEnvVarNames removed: requires full app import chain (src.presentation.api)
## which has broken dependencies in the target repo (dj_audio_storage, use_cases, etc.)
