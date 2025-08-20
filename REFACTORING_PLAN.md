# Refactoring Plan

## Decisions
- Adopted `src/` layout with a `gaij` package to isolate application code.
- Introduced `Settings` class powered by `pydantic-settings` for centralised and validated configuration.
- Added strict typing and linting; code now passes `mypy --strict` and `ruff` with selected rules.
- Created `pyproject.toml` for single-source dependency and tool configuration.
- Set up pre-commit hooks and updated CI workflow to run linting, typing, tests, security and complexity checks.

## Trade-offs
- Kept existing module APIs to preserve behaviour; further decomposition could improve testability.
- `googleapiclient` and other third‑party calls are treated as `Any` where stubs are unavailable.
- Logging remains simple text; structured JSON logging may be added later.

## Follow-ups
- Expand unit test coverage for error paths and external integrations.
- Consider extracting Gmail and Jira clients behind interfaces for easier mocking.
- Review deployment workflow after migrating to pyproject-based dependencies.
