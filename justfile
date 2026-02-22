# ABOUTME: Build recipes for development tasks.
# ABOUTME: Provides lint, test, and mutation testing commands.

build_dir := "build"

unit_test_files := "tests/test_unit_marvin.py tests/test_formatting.py tests/test_client.py tests/test_server.py"

# Run lint + format check + unit tests
check: lint test-unit
    @echo "All checks passed."

# Run linters and format check
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/

# Auto-fix lint and formatting issues
format:
    uv run ruff check --fix .
    uv run ruff format .

# Run all tests including integration and E2E
test:
    uv run pytest tests/ -v

# Run unit tests only
test-unit:
    uv run pytest {{ unit_test_files }} -v

# Run unit tests with coverage report
coverage: _build-dir
    uv run pytest {{ unit_test_files }} \
        --cov=amazing_marvin_mcp --cov-report=term-missing --cov-report=html:{{ build_dir }}/htmlcov \
        --cov-fail-under=75

# Run all mutation tests
mutate: mutate-marvin mutate-formatting

# Run mutation tests for marvin.py
mutate-marvin: _build-dir
    rm -f {{ build_dir }}/session-marvin.sqlite
    uv run cosmic-ray init cosmic-ray.toml {{ build_dir }}/session-marvin.sqlite
    uv run python -m cosmic_ray.tools.filters.operators_filter {{ build_dir }}/session-marvin.sqlite cosmic-ray.toml
    uv run cosmic-ray exec cosmic-ray.toml {{ build_dir }}/session-marvin.sqlite
    uv run cr-report {{ build_dir }}/session-marvin.sqlite > {{ build_dir }}/mutants-marvin.txt 2>&1
    @tail -1 {{ build_dir }}/mutants-marvin.txt
    uv run cr-rate --fail-over 5.0 {{ build_dir }}/session-marvin.sqlite

# Run mutation tests for formatting.py
mutate-formatting: _build-dir
    rm -f {{ build_dir }}/session-formatting.sqlite
    uv run cosmic-ray init cosmic-ray-formatting.toml {{ build_dir }}/session-formatting.sqlite
    uv run python -m cosmic_ray.tools.filters.operators_filter {{ build_dir }}/session-formatting.sqlite cosmic-ray-formatting.toml
    uv run cosmic-ray exec cosmic-ray-formatting.toml {{ build_dir }}/session-formatting.sqlite
    uv run cr-report {{ build_dir }}/session-formatting.sqlite > {{ build_dir }}/mutants-formatting.txt 2>&1
    @tail -1 {{ build_dir }}/mutants-formatting.txt
    uv run cr-rate --fail-over 22.0 {{ build_dir }}/session-formatting.sqlite

# Show cached mutation test results
mutate-report:
    @echo "=== marvin.py ==="
    @tail -3 {{ build_dir }}/mutants-marvin.txt
    @echo ""
    @echo "=== formatting.py ==="
    @tail -3 {{ build_dir }}/mutants-formatting.txt

# Remove build artifacts
clean:
    rm -rf {{ build_dir }}

# Create build directory
[private]
_build-dir:
    mkdir -p {{ build_dir }}
