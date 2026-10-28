# GitHub Gists API

A small HTTP API that returns a GitHub user's public gists.

`GET /<username>` → JSON list of that user's public gists (via the GitHub API).

## Endpoints

| Method | Path                       | Description                                   |
|--------|----------------------------|------------------------------------------------|
| GET    | `/<username>`               | Public gists for `username`                    |
| GET    | `/<username>?page=2`        | Page 2 of results (GitHub-style pagination)     |
| GET    | `/<username>?per_page=5`    | Page size, up to 100 (GitHub API max)           |
| GET    | `/health`                   | Liveness check                                  |

Example response:

```json
{
  "user": "octocat",
  "count": 8,
  "gists": [
    {
      "id": "aa5a315d61ae9438b18d",
      "description": "Hello world example",
      "public": true,
      "html_url": "https://gist.github.com/octocat/aa5a315d61ae9438b18d",
      "created_at": "2010-04-14T02:15:15Z",
      "updated_at": "2011-06-20T11:34:15Z",
      "files": ["hello_world.rb"]
    }
  ]
}
```

Errors return a JSON body with an `error` field and an appropriate status code
(`404` unknown user, `403` GitHub rate limit hit, `502` GitHub unreachable/unexpected).

## Run it with Docker (recommended — no local Python needed)

```bash
docker build -t gist-api .
docker run --rm -p 8080:8080 gist-api
```

Then:

```bash
curl http://localhost:8080/octocat
```

### Optional: authenticate to GitHub

The GitHub API allows 60 unauthenticated requests/hour per IP. To raise that
limit, pass a [personal access token](https://github.com/settings/tokens)
(no scopes needed for public data) at run time:

```bash
docker run --rm -p 8080:8080 -e GITHUB_TOKEN=ghp_xxx gist-api
```

## Run it locally (without Docker)

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main               # serves on http://localhost:8080
```

## Running the tests

Tests mock the GitHub API (via `responses`), so they run offline and fast.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -v
```

An optional integration test (`tests/test_integration.py`) hits the real
GitHub API using the `octocat` test user. It's skipped by default; to run it:

```bash
RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py -v
```

## Design notes

- **Framework**: Flask + gunicorn — minimal footprint, no unnecessary
  moving parts.
- **Caching**: a tiny in-memory TTL cache (60s by default, configurable via
  `CACHE_TTL_SECONDS`) avoids hammering the GitHub API on repeated requests
  for the same user/page. It's per-process and intentionally simple — no
  external cache dependency (e.g. Redis) is needed for this exercise.
- **Pagination**: `page` and `per_page` query params are passed straight
  through to GitHub's own pagination, so callers get familiar semantics.
- **Config**: everything runtime-tunable (`GITHUB_TOKEN`,
  `GITHUB_API_BASE`, `UPSTREAM_TIMEOUT`, `CACHE_TTL_SECONDS`) is read from
  environment variables, so the container needs no code changes to
  configure.
- **Non-root container user** and a slim base image keep the Docker image
  small and reasonably hardened without adding complexity.

## Project layout

```
.
├── app/
│   ├── __init__.py
│   └── main.py          # Flask app + route handler
├── tests/
│   ├── test_main.py         # unit tests (mocked GitHub API)
│   └── test_integration.py  # optional, real GitHub API (octocat)
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── .dockerignore
└── README.md
```
