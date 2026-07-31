import os

# Tool/API modules read KIPRIS_API_KEY at import time. Unit tests never make
# real network calls, so a placeholder is enough to let those imports succeed
# without requiring a real secret in local/CI environments.
os.environ.setdefault("KIPRIS_API_KEY", "test-key-for-unit-tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast, fully-mocked tests with no network access")
    config.addinivalue_line("markers", "integration: tests that call the live KIPRIS API")
