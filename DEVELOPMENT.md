# Development Guide

## Setup

### 1. Install Dependencies

**Python dependencies:**
```bash
# Production dependencies
uv pip install -e .

# Development dependencies (includes linting, testing, hooks)
uv pip install -e ".[dev]"
```

**Node.js dependencies (for Husky hooks):**
```bash
npm install
```

### 2. Setup Git Hooks

You can use either **pre-commit** (Python standard) or **Husky** (Node.js approach).

#### Option A: pre-commit (Recommended for Python projects)

```bash
# Install hooks
make setup-hooks

# Or manually:
pre-commit install
pre-commit install --hook-type commit-msg
```

**Run hooks manually:**
```bash
make hooks-run              # Run on all files
pre-commit run --all-files  # Same as above
```

**Update hooks:**
```bash
make hooks-update
```

#### Option B: Husky (Already configured)

Husky hooks are automatically installed when you run `npm install` (via the `prepare` script).

**What runs on commit:**
- `lint-staged`: Runs ruff linter and formatter on staged Python files
- Optional: Can uncomment test running in `.husky/pre-commit`

**NPM scripts available:**
```bash
npm run lint:python    # Lint Python code
npm run format:python  # Format Python code
npm run test:python    # Run Python tests
npm run check:python   # Lint + test
```

## Code Quality

### Linting and Formatting

**Using Make:**
```bash
make format     # Auto-format with ruff
make lint       # Check code quality
make type-check # Type check with mypy
```

**Using ruff directly:**
```bash
ruff check scripts/ tests/           # Lint
ruff check --fix scripts/ tests/     # Lint and auto-fix
ruff format scripts/ tests/          # Format
```

### Testing

**Run tests:**
```bash
make test
# or
pytest tests/ -v
```

**Run tests with coverage:**
```bash
pytest tests/ --cov=scripts --cov-report=html
```

## Pre-commit Hooks Comparison

### pre-commit (Python)
✅ **Pros:**
- Python ecosystem standard
- Rich ecosystem of hooks
- Language-agnostic (can run hooks for any language)
- Managed versions via `.pre-commit-config.yaml`
- Automatic hook updates

❌ **Cons:**
- Requires Python tool installation
- Separate from Node.js ecosystem

**Hooks configured:**
- File checks (trailing whitespace, EOF, YAML/JSON/TOML validation)
- Ruff linting and formatting
- MyPy type checking
- Bandit security checks
- Large file detection
- Private key detection

### Husky + lint-staged (Node.js)
✅ **Pros:**
- Already in your Node.js workflow
- Familiar if you know Node.js ecosystem
- Simple setup with npm/package.json
- Fast execution with lint-staged (only runs on staged files)

❌ **Cons:**
- Requires Node.js installation
- Less Python-native
- Manual version management

**Hooks configured:**
- Ruff linting and formatting on staged `.py` files
- Optional test running (commented out)
- Optional conventional commit message validation

## Recommended Workflow

1. **For Python-only development**: Use `pre-commit`
2. **For mixed Python/Node.js**: Use `Husky` (already set up)
3. **For CI/CD**: Use `pre-commit` (easier to integrate)

## Common Commands

### Development Workflow
```bash
# 1. Make changes to Python files
vim scripts/process_dump.py

# 2. Format and lint
make format

# 3. Run tests
make test

# 4. Commit (hooks run automatically)
git add scripts/process_dump.py
git commit -m "feat(scripts): improve account code padding"

# 5. Push
git push
```

### Running Scripts
```bash
# Individual scripts
python scripts/process_dump.py
python scripts/transform_trial_balances.py
python scripts/combine_databases.py

# Run all scripts in sequence
make run-all

# Or use installed CLI commands (after pip install -e .)
process-dump
transform-trial-balances
combine-databases
```

### Cleanup
```bash
make clean  # Remove cache files, __pycache__, etc.
```

## VS Code Integration

Add to `.vscode/settings.json`:
```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  },
  "python.linting.enabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"

      - name: Run pre-commit hooks
        run: pre-commit run --all-files

      - name: Run tests
        run: pytest tests/ -v
```

## Troubleshooting

**Hooks not running:**
```bash
# For pre-commit
pre-commit install --install-hooks
pre-commit run --all-files

# For Husky
npm install
```

**Ruff command not found:**
```bash
uv pip install -e ".[dev]"
```

**Tests failing:**
```bash
# Check if dependencies are installed
uv pip list
# Reinstall dev dependencies
uv pip install -e ".[dev]"
```
