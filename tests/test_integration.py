"""
Optional integration test that calls the real GitHub API (no mocking).

Skipped by default so the main test suite runs fast and offline.
Enable with: RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from app.main import app

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to run tests against the real GitHub API",
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_octocat_has_gists(client):
    resp = client.get("/octocat")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["user"] == "octocat"
    assert isinstance(data["gists"], list)
