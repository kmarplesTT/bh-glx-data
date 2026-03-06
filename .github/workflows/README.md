# GitHub Actions Workflows

This directory contains CI/CD workflows for the BH Galaxy Data Analysis Tool.

## Workflows

### 1. Tests (`tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Manual trigger via workflow_dispatch

**What it does:**
- Runs unit and integration tests on Python 3.10, 3.11, and 3.12
- Generates code coverage reports
- Uploads coverage artifacts
- Enforces minimum 80% code coverage

**Test Matrix:**
```yaml
Python Versions: 3.10, 3.11, 3.12
OS: Ubuntu Latest
```

**Coverage Reports:**
- Terminal output with missing lines
- HTML report (uploaded as artifact)
- XML report for future integrations

**Failure Conditions:**
- Any test fails
- Coverage drops below 80%

### 2. Code Quality (`lint.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Manual trigger via workflow_dispatch

**What it does:**
- Checks code formatting with `black`
- Checks import sorting with `isort`
- Lints code with `pylint` (minimum score: 7.0)
- Type checks with `mypy`

**Quality Checks:**

| Tool | Check | Threshold |
|------|-------|-----------|
| black | Code formatting | 100% compliant |
| isort | Import sorting | 100% compliant |
| pylint | Code quality | Score >= 7.0 |
| mypy | Type safety | Zero errors |

**Failure Conditions:**
- Code not formatted with black
- Imports not sorted
- Pylint score < 7.0
- Any mypy type errors

## Local Testing

Run the same checks locally before pushing:

### Run Tests
```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# With coverage
pytest tests/ --cov=src/bh_glx_data --cov-report=term-missing
```

### Run Code Quality Checks
```bash
# Format check
black --check src/bh_glx_data/ tests/

# Import sort check
isort --check src/bh_glx_data/ tests/

# Lint
pylint src/bh_glx_data/ --disable=C0114,C0115,C0116 --max-line-length=100 --fail-under=7.0

# Type check
mypy src/bh_glx_data/ --ignore-missing-imports --no-strict-optional --check-untyped-defs
```

### Auto-fix Issues
```bash
# Auto-format code
black src/bh_glx_data/ tests/

# Auto-sort imports
isort src/bh_glx_data/ tests/
```

## Badge Status

Add these badges to your README.md:

```markdown
![Tests](https://github.com/YOUR_ORG/bh-glx-data/workflows/Tests/badge.svg)
![Code Quality](https://github.com/YOUR_ORG/bh-glx-data/workflows/Code%20Quality/badge.svg)
```

## Workflow Configuration

### Caching
Both workflows use pip caching to speed up dependency installation:
```yaml
cache: 'pip'
```

### Python Versions
Tests run on multiple Python versions to ensure compatibility:
- Python 3.10 (minimum supported)
- Python 3.11 (current stable)
- Python 3.12 (latest)

### Artifacts
Coverage reports are uploaded as artifacts and retained for 30 days:
- HTML coverage report
- XML coverage report (for future integrations with Codecov, etc.)

## Extending Workflows

### Adding New Tests
1. Add test files to `tests/unit/` or `tests/integration/`
2. Tests are automatically discovered by pytest
3. No workflow changes needed

### Adding New Checks
To add additional code quality checks:
1. Add the tool to `pyproject.toml` dev dependencies
2. Add a new step in `lint.yml`
3. Update this README

### Branch Protection
Recommended branch protection rules for `main`:
- ✅ Require status checks to pass
  - Tests (Python 3.11)
  - Code Quality
- ✅ Require branches to be up to date
- ✅ Require linear history
- ⚠️ Do not allow force pushes

## Troubleshooting

### Tests Failing Locally But Pass in CI
- Check Python version: `python --version`
- Ensure clean install: `pip install -e ".[dev]"`
- Check for uncommitted changes

### Coverage Dropping Below 80%
- Add tests for new code
- Check coverage report: `coverage html` then open `htmlcov/index.html`
- Focus on uncovered lines shown in terminal output

### Type Errors
- Run `mypy` locally with same flags as CI
- Check for missing type stubs
- Add `# type: ignore` comments only when necessary

### Linting Failures
- Run `pylint` locally to see issues
- Auto-fix with `black` and `isort` where possible
- Address code quality issues or update `.pylintrc` if needed

## Future Enhancements

Potential additions to CI/CD:
- [ ] Security scanning (Bandit, Safety)
- [ ] Documentation building and deployment
- [ ] Release automation
- [ ] Dependency updates (Dependabot)
- [ ] Performance benchmarking
- [ ] Code coverage reporting (Codecov integration)

---

**Last Updated:** 2026-03-05
