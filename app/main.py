"""
Simple HTTP API that returns a GitHub user's public gists.

GET /<username>            -> first page of public gists (30 per page, GitHub default)
GET /<username>?page=2     -> page 2 of results
GET /<username>?per_page=5 -> control page size (max 100, per GitHub API)
GET /health                -> liveness check
"""
import os
import time
from flask import Flask, jsonify, request
import requests

GITHUB_API_BASE = os.environ.get("GITHUB_API_BASE", "https://api.github.com")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # optional, raises the rate limit
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("UPSTREAM_TIMEOUT", "5"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "60"))

app = Flask(__name__)

# very small in-memory cache: {(username, page, per_page): (expiry_ts, payload)}
_cache = {}


def _github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _simplify(gist):
    """Return only the fields useful to a caller of this API."""
    return {
        "id": gist.get("id"),
        "description": gist.get("description"),
        "public": gist.get("public"),
        "html_url": gist.get("html_url"),
        "created_at": gist.get("created_at"),
        "updated_at": gist.get("updated_at"),
        "files": list((gist.get("files") or {}).keys()),
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/<username>")
def get_user_gists(username):
    page = request.args.get("page", "1")
    per_page = request.args.get("per_page", "30")

    cache_key = (username, page, per_page)
    cached = _cache.get(cache_key)
    if cached and cached[0] > time.time():
        return jsonify(cached[1])

    try:
        response = requests.get(
            f"{GITHUB_API_BASE}/users/{username}/gists",
            headers=_github_headers(),
            params={"page": page, "per_page": per_page},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": "Failed to reach GitHub API", "details": str(exc)}), 502

    if response.status_code == 404:
        return jsonify({"error": f"GitHub user '{username}' not found"}), 404

    if response.status_code == 403:
        return jsonify({"error": "GitHub API rate limit exceeded"}), 403

    if response.status_code != 200:
        return jsonify(
            {"error": "Unexpected response from GitHub API", "status_code": response.status_code}
        ), 502

    gists = [_simplify(g) for g in response.json()]
    payload = {"user": username, "count": len(gists), "gists": gists}

    if CACHE_TTL_SECONDS > 0:
        _cache[cache_key] = (time.time() + CACHE_TTL_SECONDS, payload)

    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
