# Contributing

## Architecture

```
server.py  →  marvin.py  →  client.py  →  Amazing Marvin API
(MCP)         (logic)       (HTTP)
```

- **`server.py`**: Thin MCP adapter — registers tools, delegates to business logic. Uses `@_handle_errors` decorator for consistent error responses.
- **`marvin.py`**: Intent-oriented operations — name resolution, caching, timezone detection
- **`client.py`**: Raw HTTP — auth headers, rate limiting, error mapping
- **`formatting.py`**: Markdown conversion and response trimming

## Setup

Requires [just](https://github.com/casey/just#installation) and [uv](https://docs.astral.sh/uv/). If you use [mise](https://mise.jdx.dev/), `mise install` will set up both.

```bash
mise install      # optional, installs just + uv
uv sync
uv run pre-commit install
```

## Development Commands

All development tasks have justfile recipes. Use these instead of running tools directly.

| Command | Purpose |
|---------|---------|
| `just lint` | Run ruff check, ruff format check, and mypy |
| `just format` | Auto-fix lint and formatting issues |
| `just test` | Run all tests |
| `just test-unit` | Run unit tests only (no API calls) |
| `just coverage` | Unit tests with coverage report |
| `just check` | Lint + unit tests |
| `just mutate` | Run mutation testing on marvin.py and formatting.py |
| `just mutate-report` | Show cached mutation testing results |
| `just clean` | Remove build artifacts |

Integration and E2E tests require `MARVIN_API_TOKEN` to be set.

## CI

GitHub Actions runs `just check`, `just coverage`, and `just mutate` on every push to main and on pull requests. CI installs `just` via `extractions/setup-just@v3`. Coverage and mutation reports are uploaded as build artifacts. See `.github/workflows/ci.yml`.

**Thresholds** (CI fails if these regress):
- Coverage: 75% minimum (unit tests only; integration/E2E cover the rest)
- Mutation survival: marvin.py ≤60%, formatting.py ≤43% (includes equivalent type annotation mutants)

## Pre-Commit Checklist

Before committing, verify:

- [ ] `just check` passes (lint + unit tests)
- [ ] Public API changes are reflected in README.md (tools, prompts, library usage)
- [ ] No compatibility shims for older Python versions (target is 3.11+)

Pre-commit hooks run ruff check and format automatically. Heavier checks (mypy, tests, mutation) run in CI.

## Pre-PR Checklist

Before opening a pull request, also verify:

- [ ] `just mutate` run against any new or changed tests
- [ ] Mutation kill rates haven't regressed (check `just mutate-report` against previous run)

## Testing Strategy

- **Unit tests** (`test_unit_marvin.py`, `test_formatting.py`, `test_client.py`, `test_server.py`): Business logic with mocked HTTP client. Fast, no API calls.
- **Integration tests** (`test_marvin_integration.py`, `test_integration.py`): Validate real API contract and formatting with real data. Require `MARVIN_API_TOKEN`.
- **E2E tests** (`test_e2e.py`): Core MCP server flows over STDIO transport.
- **Mutation testing**: cosmic-ray against unit tests. Results go to `build/`. Run `just mutate-report` to see current kill rates.

## Key Constraints

- **Rate limiting**: Amazing Marvin API enforces 3s between queries, 1s between mutations. This is handled in `client.py` and is why integration tests are slow.
- **Auth**: Use `X-Full-Access-Token` header only. Sending both `X-API-Token` and `X-Full-Access-Token` causes auth failure.
- **Security**: See [SECURITY.md](SECURITY.md) for the full security model — token handling, transport security, and authorization boundaries.
- **Test sandbox**: Integration tests create tasks under the "MCP Test" category and clean up after themselves.
