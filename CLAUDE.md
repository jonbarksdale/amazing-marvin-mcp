# Project Instructions

## Commands

Use Makefile targets for all development tasks. Never run ruff, mypy, pytest, or cosmic-ray directly.

- `make check` — lint + unit tests (run before every commit)
- `make test` — all tests including integration and E2E
- `make mutate` — mutation testing (run after adding or changing tests)
- `make mutate-report` — show cached mutation results

## Verification Workflow

1. `make check` before every commit
2. `make mutate` after adding or changing tests, and before marking a task complete
3. Check README.md when changing public API (tools, prompts, library interface)

## Python Version

Target is Python 3.11+. Do not use `from __future__ import annotations` or other compatibility shims. Use `typing.Self` for self-referencing return types.

## Project Conventions

- See CONTRIBUTING.md for architecture, testing strategy, and key constraints.
- The Amazing Marvin API uses `X-Full-Access-Token` only (not `X-API-Token`).
- Integration tests use "MCP Test" category as a sandbox parent.
