# ABOUTME: Build targets for development tasks.
# ABOUTME: Provides lint, test, and mutation testing commands.

BUILD_DIR := build

.PHONY: lint format test test-unit coverage mutate mutate-marvin mutate-formatting mutate-report check clean

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/test_unit_marvin.py tests/test_formatting.py tests/test_client.py tests/test_server.py -v

coverage: $(BUILD_DIR)
	uv run pytest tests/test_unit_marvin.py tests/test_formatting.py tests/test_client.py tests/test_server.py \
		--cov=amazing_marvin_mcp --cov-report=term-missing --cov-report=html:$(BUILD_DIR)/htmlcov

check: lint test-unit
	@echo "All checks passed."

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

mutate: mutate-marvin mutate-formatting

mutate-marvin: $(BUILD_DIR)
	@rm -f $(BUILD_DIR)/session-marvin.sqlite
	uv run cosmic-ray init cosmic-ray.toml $(BUILD_DIR)/session-marvin.sqlite
	uv run cosmic-ray exec cosmic-ray.toml $(BUILD_DIR)/session-marvin.sqlite
	uv run cr-report $(BUILD_DIR)/session-marvin.sqlite > $(BUILD_DIR)/mutants-marvin.txt 2>&1
	@tail -1 $(BUILD_DIR)/mutants-marvin.txt

mutate-formatting: $(BUILD_DIR)
	@rm -f $(BUILD_DIR)/session-formatting.sqlite
	uv run cosmic-ray init cosmic-ray-formatting.toml $(BUILD_DIR)/session-formatting.sqlite
	uv run cosmic-ray exec cosmic-ray-formatting.toml $(BUILD_DIR)/session-formatting.sqlite
	uv run cr-report $(BUILD_DIR)/session-formatting.sqlite > $(BUILD_DIR)/mutants-formatting.txt 2>&1
	@tail -1 $(BUILD_DIR)/mutants-formatting.txt

mutate-report:
	@echo "=== marvin.py ==="
	@tail -3 $(BUILD_DIR)/mutants-marvin.txt
	@echo ""
	@echo "=== formatting.py ==="
	@tail -3 $(BUILD_DIR)/mutants-formatting.txt

clean:
	rm -rf $(BUILD_DIR)
