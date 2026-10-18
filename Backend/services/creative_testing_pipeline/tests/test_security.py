"""
Tests for ACTP Security Module
"""

import pytest

from services.creative_testing_pipeline.security import (
    InputSanitizer,
    RateLimiter,
    SecretsValidator,
    ACTPErrorHandler,
)


class TestInputSanitizer:
    """Test input sanitization."""

    def test_sanitize_html_escaping(self):
        result = InputSanitizer.sanitize_text("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_enforces_length(self):
        long = "x" * 1000
        result = InputSanitizer.sanitize_text(long, "hook")
        assert len(result) <= 500

    def test_sanitize_name_limit(self):
        long = "a" * 300
        result = InputSanitizer.sanitize_text(long, "name")
        assert len(result) <= 200

    def test_sanitize_url_valid(self):
        url = "https://example.com/offer?utm=test"
        result = InputSanitizer.sanitize_url(url)
        assert result == url

    def test_sanitize_url_rejects_private(self):
        with pytest.raises(ValueError, match="Internal/private"):
            InputSanitizer.sanitize_url("http://localhost:3000/api")

    def test_sanitize_url_rejects_bad_scheme(self):
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            InputSanitizer.sanitize_url("ftp://example.com/file")

    def test_sanitize_dict_recursive(self):
        data = {
            "name": "<b>Test</b>",
            "nested": {"hook": "<script>bad</script>"},
            "tags": ["<em>tag</em>", "normal"],
            "count": 5,
        }
        result = InputSanitizer.sanitize_dict(data)
        assert "&lt;b&gt;" in result["name"]
        assert "<script>" not in result["nested"]["hook"]
        assert result["count"] == 5

    def test_validate_file_upload_valid(self):
        assert InputSanitizer.validate_file_upload("video.mp4", "video/mp4", 10_000_000)

    def test_validate_file_upload_bad_type(self):
        with pytest.raises(ValueError, match="Invalid file type"):
            InputSanitizer.validate_file_upload("doc.pdf", "application/pdf", 1000)

    def test_validate_file_upload_too_large(self):
        with pytest.raises(ValueError, match="File too large"):
            InputSanitizer.validate_file_upload("big.mp4", "video/mp4", 600_000_000, max_size_mb=500)

    def test_validate_file_upload_bad_extension(self):
        with pytest.raises(ValueError, match="Invalid file extension"):
            InputSanitizer.validate_file_upload("video.exe", "video/mp4", 1000)


class TestRateLimiter:
    """Test rate limiting."""

    def test_allows_within_limit(self):
        limiter = RateLimiter(requests_per_minute=5)
        for _ in range(5):
            assert limiter.check("1.2.3.4") is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(requests_per_minute=3)
        for _ in range(3):
            limiter.check("1.2.3.4")
        assert limiter.check("1.2.3.4") is False

    def test_different_ips_independent(self):
        limiter = RateLimiter(requests_per_minute=2)
        limiter.check("1.1.1.1")
        limiter.check("1.1.1.1")
        assert limiter.check("1.1.1.1") is False
        assert limiter.check("2.2.2.2") is True

    def test_retry_after_positive(self):
        limiter = RateLimiter(requests_per_minute=1)
        limiter.check("1.1.1.1")
        limiter.check("1.1.1.1")
        retry = limiter.get_retry_after("1.1.1.1")
        assert retry >= 0


class TestSecretsValidator:
    """Test secrets validation."""

    def test_validate_required_returns_dict(self):
        status = SecretsValidator.validate_required()
        assert isinstance(status, dict)
        assert "SUPABASE_URL" in status
        assert "SUPABASE_KEY" in status

    def test_validate_optional_returns_dict(self):
        status = SecretsValidator.validate_optional()
        assert isinstance(status, dict)
        assert "OPENAI_API_KEY" in status

    def test_provider_availability_returns_dict(self):
        avail = SecretsValidator.get_provider_availability()
        assert isinstance(avail, dict)
        assert "sora" in avail
        assert "meta_ads" in avail


class TestErrorHandler:
    """Test standardized error responses."""

    def test_known_status_code(self):
        resp = ACTPErrorHandler.error_response(404, "Campaign not found")
        assert resp["error"] == "not_found"
        assert resp["message"] == "Campaign not found"
        assert resp["status_code"] == 404

    def test_default_message(self):
        resp = ACTPErrorHandler.error_response(400)
        assert resp["message"] == "Invalid request"

    def test_unknown_status_code(self):
        resp = ACTPErrorHandler.error_response(418)
        assert resp["error"] == "error"

    def test_with_field_errors(self):
        errors = [{"field": "name", "message": "required"}]
        resp = ACTPErrorHandler.error_response(422, errors=errors)
        assert resp["errors"] == errors

    def test_raise_safe(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            ACTPErrorHandler.raise_safe(403, "Not allowed")
        assert exc_info.value.status_code == 403
