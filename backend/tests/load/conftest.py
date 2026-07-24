"""Pytest fixtures for load tests (if run via pytest)."""

# Reuse integration test fixtures
pytest_plugins = ["backend.tests.integration.conftest"]
