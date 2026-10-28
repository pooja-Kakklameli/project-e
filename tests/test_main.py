import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import responses

from app.main import app, GITHUB_API_BASE, _cache


@pytest.fixture
def client():
    app.config["TESTING"] = True
    _cache.clear()
    with app.test_client() as c:
        yield c


SAMPLE_GIST = {
    "id": "aa5a315d61ae9438b18d",
    "description": "Hello world example",
    "public": True,
    "html_url": "https://gist.github.com/octocat/aa5a315d61ae9438b18d",
    "created_at": "2010-04-14T02:15:15Z",
    "updated_at": "2011-06-20T11:34:15Z",
    "files": {"hello_world.rb": {"filename": "hello_world.rb"}},
}


@responses.activate
def test_returns_gists_for_known_user(client):
    responses.add(
        responses.GET,
        f"{GITHUB_API_BASE}/users/octocat/gists",
        json=[SAMPLE_GIST],
        status=200,
    )

    resp = client.get("/octocat")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["user"] == "octocat"
    assert data["count"] == 1
    assert data["gists"][0]["id"] == SAMPLE_GIST["id"]
    assert data["gists"][0]["files"] == ["hello_world.rb"]


@responses.activate
def test_returns_empty_list_for_user_with_no_gists(client):
    responses.add(
        responses.GET,
        f"{GITHUB_API_BASE}/users/no-gists-user/gists",
        json=[],
        status=200,
    )

    resp = client.get("/no-gists-user")

    assert resp.status_code == 200
    assert resp.get_json() == {"user": "no-gists-user", "count": 0, "gists": []}


@responses.activate
def test_returns_404_for_unknown_user(client):
    responses.add(
        responses.GET,
        f"{GITHUB_API_BASE}/users/definitely-not-a-real-user-12345/gists",
        json={"message": "Not Found"},
        status=404,
    )

    resp = client.get("/definitely-not-a-real-user-12345")

    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"].lower()


@responses.activate
def test_returns_403_on_rate_limit(client):
    responses.add(
        responses.GET,
        f"{GITHUB_API_BASE}/users/octocat/gists",
        json={"message": "API rate limit exceeded"},
        status=403,
    )

    resp = client.get("/octocat")

    assert resp.status_code == 403


@responses.activate
def test_passes_pagination_params_through(client):
    responses.add(
        responses.GET,
        f"{GITHUB_API_BASE}/users/octocat/gists",
        json=[SAMPLE_GIST],
        status=200,
    )

    resp = client.get("/octocat?page=2&per_page=5")

    assert resp.status_code == 200
    sent_request = responses.calls[0].request
    assert "page=2" in sent_request.url
    assert "per_page=5" in sent_request.url


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
