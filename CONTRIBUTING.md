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

```bash
uv sync
uv run pre-commit install
```

## Development Commands

All development tasks have Makefile targets. Use these instead of running tools directly.

| Command | Purpose |
|---------|---------|
| `make lint` | Run ruff check, ruff format check, and mypy |
| `make format` | Auto-fix lint and formatting issues |
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only (no API calls) |
| `make coverage` | Unit tests with coverage report |
| `make check` | Lint + unit tests |
| `make mutate` | Run mutation testing on marvin.py and formatting.py |
| `make mutate-report` | Show cached mutation testing results |
| `make clean` | Remove build artifacts |

Integration and E2E tests require `MARVIN_API_TOKEN` to be set.

## CI

GitHub Actions runs `make check`, `make coverage`, and `make mutate` on every push to main and on pull requests. Coverage and mutation reports are uploaded as build artifacts. See `.github/workflows/ci.yml`.

**Thresholds** (CI fails if these regress):
- Coverage: 75% minimum (unit tests only; integration/E2E cover the rest)
- Mutation survival: marvin.py ≤60%, formatting.py ≤43% (includes equivalent type annotation mutants)

## Pre-Commit Checklist

Before committing, verify:

- [ ] `make check` passes (lint + unit tests)
- [ ] Public API changes are reflected in README.md (tools, prompts, library usage)
- [ ] No compatibility shims for older Python versions (target is 3.11+)

Pre-commit hooks run ruff check and format automatically. Heavier checks (mypy, tests, mutation) run in CI.

## Pre-PR Checklist

Before opening a pull request, also verify:

- [ ] `make mutate` run against any new or changed tests
- [ ] Mutation kill rates haven't regressed (check `make mutate-report` against previous run)

## Testing Strategy

- **Unit tests** (`test_unit_marvin.py`, `test_formatting.py`, `test_client.py`, `test_server.py`): Business logic with mocked HTTP client. Fast, no API calls.
- **Integration tests** (`test_marvin_integration.py`, `test_integration.py`): Validate real API contract and formatting with real data. Require `MARVIN_API_TOKEN`.
- **E2E tests** (`test_e2e.py`): Core MCP server flows over STDIO transport.
- **Mutation testing**: cosmic-ray against unit tests. Results go to `build/`. Run `make mutate-report` to see current kill rates.

## Key Constraints

- **Rate limiting**: Amazing Marvin API enforces 3s between queries, 1s between mutations. This is handled in `client.py` and is why integration tests are slow.
- **Auth**: Use `X-Full-Access-Token` header only. Sending both `X-API-Token` and `X-Full-Access-Token` causes auth failure.
- **Security**: See [SECURITY.md](SECURITY.md) for the full security model — token handling, transport security, and authorization boundaries.
- **Test sandbox**: Integration tests create tasks under the "MCP Test" category and clean up after themselves.
