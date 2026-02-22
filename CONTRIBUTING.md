# Contributing

## Architecture

```
server.py  →  marvin.py  →  client.py  →  Amazing Marvin API
(MCP)         (logic)       (HTTP)
```

- **`server.py`**: Thin MCP adapter — registers tools, delegates to business logic
- **`marvin.py`**: Intent-oriented operations — name resolution, caching, timezone detection
- **`client.py`**: Raw HTTP — auth headers, rate limiting, error mapping
- **`formatting.py`**: Markdown conversion and response trimming

## Development Commands

All development tasks have Makefile targets. Use these instead of running tools directly.

| Command | Purpose |
|---------|---------|
| `make lint` | Run ruff and mypy |
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only (no API calls) |
| `make check` | Lint + unit tests |
| `make mutate` | Run mutation testing on marvin.py and formatting.py |
| `make mutate-report` | Show cached mutation testing results |
| `make clean` | Remove build artifacts |

Integration and E2E tests require `MARVIN_API_TOKEN` to be set.

## Pre-Commit Checklist

Before committing, verify:

- [ ] `make check` passes (lint + unit tests)
- [ ] Public API changes are reflected in README.md (tools, prompts, library usage)
- [ ] No compatibility shims for older Python versions (target is 3.11+)

## Pre-PR Checklist

Before opening a pull request, also verify:

- [ ] `make mutate` run against any new or changed tests
- [ ] Mutation kill rates haven't regressed (marvin.py ~98%, formatting.py ~85% effective)

## Testing Strategy

- **Unit tests** (`test_unit_marvin.py`, `test_formatting.py`, `test_client.py`, `test_server.py`): Business logic with mocked HTTP client. Fast, no API calls.
- **Integration tests** (`test_marvin.py`): Validate real API contract. Require `MARVIN_API_TOKEN`.
- **E2E tests** (`test_e2e.py`): Core MCP server flows over STDIO transport.
- **Mutation testing**: cosmic-ray against unit tests. Results go to `build/`. Expect ~98% effective kill rate on marvin.py and ~85% on formatting.py (excluding equivalent type annotation mutants).

## Key Constraints

- **Rate limiting**: Amazing Marvin API enforces 3s between queries, 1s between mutations. This is handled in `client.py` and is why integration tests are slow.
- **Auth**: Use `X-Full-Access-Token` header only. Sending both `X-API-Token` and `X-Full-Access-Token` causes auth failure.
- **Test sandbox**: Integration tests create tasks under the "MCP Test" category and clean up after themselves.
