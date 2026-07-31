import logging

import pytest

from mcp_kipris.kipris.logging_utils import (
    create_safe_url_logger,
    get_log_level_from_env,
    redact_sensitive_data,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw,should_contain",
    [
        ("https://api.example.com?accessKey=SECRET123&foo=bar", "***REDACTED***"),
        ("ServiceKey=SECRET123", "***REDACTED***"),
        ("Authorization: Bearer abc.def-ghi", "***REDACTED***"),
    ],
)
def test_redact_sensitive_data_masks_known_patterns(raw, should_contain):
    redacted = redact_sensitive_data(raw)

    assert should_contain in redacted
    assert "SECRET123" not in redacted


def test_redact_sensitive_data_leaves_plain_text_untouched():
    assert redact_sensitive_data("no secrets here") == "no secrets here"


def test_redact_sensitive_data_coerces_non_string_input():
    assert redact_sensitive_data(404) == "404"


def test_get_log_level_from_env_defaults_to_info(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert get_log_level_from_env() == logging.INFO


def test_get_log_level_from_env_reads_valid_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")

    assert get_log_level_from_env() == logging.DEBUG


def test_get_log_level_from_env_falls_back_on_unknown_value(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "not-a-real-level")

    assert get_log_level_from_env() == logging.INFO


def test_safe_url_logger_redacts_urls_before_delegating():
    captured = {}

    class _FakeLogger:
        def log(self, level, msg, *args, **kwargs):
            captured["level"] = level
            captured["msg"] = msg

    safe_logger = create_safe_url_logger(_FakeLogger())
    safe_logger.info("calling http://api.example.com?accessKey=SECRET123")

    assert captured["level"] == logging.INFO
    assert "SECRET123" not in captured["msg"]


def test_safe_url_logger_passes_through_non_url_messages():
    captured = {}

    class _FakeLogger:
        def log(self, level, msg, *args, **kwargs):
            captured["msg"] = msg

    safe_logger = create_safe_url_logger(_FakeLogger())
    safe_logger.warning("plain warning message")

    assert captured["msg"] == "plain warning message"
