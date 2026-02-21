# ABOUTME: Build targets for development tasks.
# ABOUTME: Provides lint, test, and mutation testing commands.

.PHONY: lint test mutate mutate-marvin mutate-formatting

lint:
	uv run ruff check .
	uv run mypy src/

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/test_unit_marvin.py tests/test_formatting.py tests/test_client.py tests/test_server.py -v

mutate: mutate-marvin mutate-formatting

mutate-marvin:
	@rm -f session.sqlite
	uv run cosmic-ray init cosmic-ray.toml session.sqlite
	uv run cosmic-ray exec cosmic-ray.toml session.sqlite
	@uv run cr-report session.sqlite 2>&1 | tail -1

mutate-formatting:
	@rm -f session-formatting.sqlite
	uv run cosmic-ray init cosmic-ray-formatting.toml session-formatting.sqlite
	uv run cosmic-ray exec cosmic-ray-formatting.toml session-formatting.sqlite
	@uv run cr-report session-formatting.sqlite 2>&1 | tail -1
