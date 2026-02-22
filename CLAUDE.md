# Project Instructions

## Commands

Use justfile recipes for all development tasks. Never run ruff, mypy, pytest, or cosmic-ray directly.

- `just check` — lint + format check + unit tests (run before every commit)
- `just format` — auto-fix lint and formatting issues
- `just coverage` — unit tests with coverage report
- `just test` — all tests including integration and E2E
- `just mutate` — mutation testing (run after adding or changing tests)
- `just mutate-report` — show cached mutation results

## Verification Workflow

1. `just check` before every commit
2. `just mutate` after adding or changing tests, and before marking a task complete
3. Check README.md when changing public API (tools, prompts, library interface)

## Python Version

Target is Python 3.11+. Do not use `from __future__ import annotations` or other compatibility shims. Use `typing.Self` for self-referencing return types.

## Project Conventions

- See CONTRIBUTING.md for architecture, testing strategy, and key constraints.
- See SECURITY.md for auth model, transport security, and token handling requirements.
- The Amazing Marvin API uses `X-Full-Access-Token` only (not `X-API-Token`).
- All tool handlers use the `@_handle_errors` decorator for consistent error handling.
- Integration tests use "MCP Test" category as a sandbox parent.
