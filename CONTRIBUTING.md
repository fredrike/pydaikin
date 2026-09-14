# Contributing to PyDaikin

Thank you for your interest in contributing to PyDaikin! We welcome contributions from the community to help improve this library for controlling Daikin air conditioners.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

Please be respectful and considerate in all interactions. We aim to foster an open and welcoming environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pydaikin.git
   cd pydaikin
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/fredrike/pydaikin.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- Git

### Install Dependencies

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/macOS
   # or
   venv\Scripts\activate  # On Windows
   ```

2. **Install the package in development mode**:
   ```bash
   pip install -e .
   ```

3. **Install development dependencies**:
   ```bash
   pip install -r requirements-test.txt
   pip install ruff pylint
   ```

### Setting Up Pre-commit Hooks (Recommended)

Pre-commit hooks automatically check your code before each commit, ensuring code quality and consistency.

1. **Install pre-commit**:
   ```bash
   pip install pre-commit
   ```

2. **Install the git hooks**:
   ```bash
   pre-commit install
   ```

3. **Run pre-commit on all files** (optional, for initial setup):
   ```bash
   pre-commit run --all-files
   ```

**What happens when you commit:**
- Pre-commit automatically runs ruff (formatting, linting, and import sorting)
- If any check fails or files are modified, the commit is aborted
- Review the changes, stage them with `git add`, and commit again
- This ensures all committed code meets quality standards

**Skip pre-commit hooks** (not recommended, but sometimes necessary):
```bash
git commit --no-verify -m "Your commit message"
```

## Making Changes

1. **Create a new branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   or
   ```bash
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes** in the code

3. **Test your changes** (see [Testing](#testing) section)

4. **Commit your changes** with clear commit messages:
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```

## Code Style

PyDaikin follows Python coding standards and uses automated tools to maintain code quality.

### Formatting

We use **ruff** for code formatting and import sorting:

```bash
# Format code with ruff
ruff format .

# Sort imports with ruff
ruff check --select I --fix .
```

**String Quote Style:** Currently, we preserve the original quote style (single or double quotes) in code. However, for **new Python files** or significant refactoring, prefer using **double quotes (`"`)** to align with Python conventions and prepare for future migration to standard string normalization. Pull requests will include an automated check that highlights single quotes in new code as a friendly reminder.

**Note:** If you have pre-commit hooks installed, these checks run automatically on commit.

### Linting

We use **ruff** and **pylint** to enforce code quality:

```bash
# Run ruff
ruff check

# Run pylint (configured in CI)
pylint pydaikin
```

**Note:** If you have pre-commit hooks installed, these checks run automatically on commit.

### Code Style Guidelines

- Follow PEP 8 conventions
- Use descriptive variable and function names
- Add docstrings to all public classes, methods, and functions
- Keep functions focused and concise
- Use type hints where appropriate
- Prefer async/await patterns for I/O operations

## Testing

### Running Tests

Run the test suite with pytest:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_daikin_base.py

# Run with coverage report
pytest --cov=pydaikin --cov-report=html
```

### Writing Tests

- Write tests for all new features and bug fixes
- Place tests in the `tests/` directory
- Use descriptive test names that explain what is being tested
- Use `pytest-asyncio` for testing async functions
- Mock external API calls using `aresponses` or similar tools
- Aim for good test coverage of your changes (the CI job reports coverage to Codecov)

**Pytest-asyncio gotchas:**

- Every async test needs an explicit `@pytest.mark.asyncio` decorator. Without it the test is **silently skipped**, not failed.
- Mark async fixtures with `@pytest_asyncio.fixture` (see `tests/test_daikin_brp084.py` for a session fixture example).

**Mocking HTTP with `aresponses`:**

- Register `path_pattern`, `method_pattern` and `response` per endpoint, and assert every registered route was used (`aresponses.assert_all_requests_matched()`).
- The `tenacity` retry wrapper retries failed requests 3 times (`stop_after_attempt(3)`), so error-path tests must register the route once per attempt, otherwise the final `assert_all_requests_matched()` fails (see `tests/test_brp069_setters.py`).

**Test isolation:**

- Run pytest **single-process**. Parallel workers (e.g. `pytest-xdist`) reuse the same loopback ports as `aresponses` and cause flaky failures.
- For tests that spin up a fake HTTP server, bind to an ephemeral port (`port=0`) and read the actual bound port afterwards instead of hard-coding one that may already be in use. If the device class hard-codes a port, monkeypatch its base URL to the ephemeral port (see `tests/test_multiple_devices.py`).

**Time-dependent code (power/energy estimation):**

- Use `freezegun.freeze_time` together with `ft.tick(...)` to simulate hours of real-time consumption in a few seconds (see `tests/test_power_sensor.py`).
- Prefer asserting invariants that hold by construction over exact values when the code under test is inherently stochastic (e.g. the slope-based power estimate is only exact for regular tick intervals).

**Keeping test data in sync:**

- The mock responses used by the tests mirror real device traffic; when you touch the API parsing, keep `docs/sample_requests/` in sync with the mocks so samples stay reproducible (see `docs/sample_requests/brp084/`).

Example test structure:
```python
import pytest
from pydaikin.daikin_base import Appliance


@pytest.mark.asyncio
async def test_your_feature():
    """Test description of what this test validates."""
    # Arrange
    device = Appliance("192.168.1.1")

    # Act
    result = await device.your_method()

    # Assert
    assert result == expected_value
```

## Submitting Changes

1. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub:
   - Go to the [PyDaikin repository](https://github.com/fredrike/pydaikin)
   - Click "New Pull Request"
   - Select your fork and branch
   - Provide a clear title and description

3. **Pull Request Guidelines**:
   - Reference any related issues (e.g., "Fixes #123")
   - Describe what changes you made and why
   - Include screenshots or logs if applicable
   - Ensure all CI checks pass
   - Be responsive to feedback and requested changes

4. **After submission**:
   - Maintainers will review your PR
   - Address any requested changes
   - Once approved, your PR will be merged

## Reporting Bugs

If you find a bug, please create an issue on GitHub with:

- **Clear title** describing the problem
- **Steps to reproduce** the issue
- **Expected behavior** vs. **actual behavior**
- **Environment details**:
  - Python version
  - PyDaikin version
  - Daikin device model and firmware version
  - Operating system
- **Relevant logs or error messages**
- **Sample code** that reproduces the issue (if applicable)

## Suggesting Enhancements

We welcome feature requests and enhancement suggestions! Please create an issue with:

- **Clear description** of the proposed feature
- **Use case** explaining why this would be useful
- **Potential implementation approach** (if you have ideas)
- **Compatibility considerations** with existing devices

## Device Support

If you're adding support for a new Daikin device:

1. **Gather device information**:
   - Document the device model and firmware version
   - Capture sample API responses (see `docs/sample_requests/` for examples)
   - Note any unique features or differences

2. **Implementation**:
   - Create a new device class inheriting from appropriate base class
   - Add tests with mocked responses
   - Update README.md with device information

3. **Documentation**:
   - Add sample request/response data to `docs/sample_requests/`
   - Update the supported devices list in README.md

## Questions?

If you have questions about contributing, feel free to:
- Open an issue on GitHub
- Check existing issues and pull requests for similar topics
- Review the [documentation](https://github.com/fredrike/pydaikin)

Thank you for contributing to PyDaikin! 🎉
