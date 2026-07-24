"""Pytest configuration for load tests."""

# Load test imports integration fixtures automatically
# via pytest.ini or command line. This file only provides
# load-test-specific fixtures if needed.

import pytest


@pytest.fixture(scope="session")
def load_test_settings():
    """Load test configuration settings."""
    return {
        "base_url": "http://localhost:8000",
        "default_users": 50,
        "spawn_rate": 5,
        "run_time": "30s",
    }
