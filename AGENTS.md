# AGENTS.md (pydaikin)

## Project
pydaikin is a Python (>=3.12) library for interfacing with Daikin HVAC appliances.

## Dependencies
- Core: `netifaces`, `aiohttp`, `urllib3`, `tenacity`
- Avoid adding new dependencies without discussion.

## Setup
- Python: 3.12
- Create venv:
  - `python -m venv .venv`
  - `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
- Install the package in editable mode:
  - `pip install -U pip`
  - `pip install -e .`

## Code quality (pre-commit)
All code quality is enforced via [pre-commit](https://pre-commit.com/).
Run all hooks before committing:
```sh
pre-commit run --all-files
```
Individual hooks:
- **ruff check** — linting with auto-fix (`--fix`), replaces flake8/isort/pylint for most rules
- **ruff format** — formatter (line length 88, target py312+), replaces black
- **pylint** — static analysis (excludes `tests/`, extends `netifaces`)

Configuration for ruff lives in `pyproject.toml` under `[tool.ruff]`.

## Quoting convention
**New code must use double quotes (`"`) for strings.**
The codebase historically uses single quotes; do not mass-reformat existing code, but all new strings should be `"double-quoted"`.

Ruff format uses `quote-style = "preserve"` so it won't change existing quotes.
Ruff lint has `inline-quotes = "double"` so it will flag single-quoted strings in new code.

## Testing
- Run tests with `pytest`.
- Test cases should prefer mocked replies using `aresponses` (see existing tests for patterns).
- If integration/device tests exist, prefer running unit tests first; only run integration when the necessary network/device setup is available.

## Type checking
- Keep interfaces type-hinted (especially public APIs).

## Python style rules
- Follow the existing code style and patterns in the repository.
- Keep functions/methods small and named clearly.
- Prefer explicit error handling; don't silently swallow exceptions.
- Prefer docstrings for non-obvious behavior (Google style is configured).

## Security / safety
- Never include real credentials/tokens/device secrets in code, docs, or tests.
- Avoid logging sensitive values (tokens, passwords, private identifiers).

## Change discipline
- For bug fixes: add/adjust tests for the failing case.
- For features: update documentation/examples if they exist and add coverage.
- Keep PRs focused and diffs small with one logical change per PR.
