# Import & Dependency Analyzer Skill

Analyze Python imports, detect circular dependencies, and validate import standards.

## Metadata

- **Name**: Import & Dependency Analyzer
- **Category**: Code Quality & Architecture
- **Activation**: Automatic when import issues mentioned
- **Model**: Haiku (fast checks) or Sonnet (deep analysis)
- **Token Cost**: ~600 tokens

## When to Activate

Trigger this skill when user mentions:
- "Import error"
- "ModuleNotFoundError"
- "Circular dependency"
- "Import validation"
- "Check imports"
- "Undefined names"
- "Missing imports"

## Import Standards (Project-Specific)

### Rule 1: ALL Imports at Top of File

```python
# CORRECT - PEP 8 compliant
import asyncio
import os
from datetime import datetime
from typing import Optional, List

from openpyxl.styles import Font
import pandas as pd

from app.domain.export.excel.constants.colors import ExcelColors
from app.shared.logging import get_logger

logger = get_logger(__name__)

def my_function():
    # Use imports here
    pass


# INCORRECT - Lazy imports (15-20% performance penalty)
def my_function():
    import asyncio  # BAD! Import inside function
    from app.domain import ExcelColors  # BAD!
    pass
```

### Rule 2: Import Organization (3 Groups)

```python
# GROUP 1: Standard library
import asyncio
import os
from datetime import datetime

# GROUP 2: Third-party
import pandas as pd
from openpyxl.styles import Font

# GROUP 3: Local application
from app.domain.export.excel.constants.colors import ExcelColors
from app.shared.logging import get_logger
```

### Rule 3: Optional Dependencies Pattern

```python
# CORRECT - Feature flag for optional dependency
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Later in code
if PSUTIL_AVAILABLE:
    memory = psutil.virtual_memory()
```

### Rule 4: No Duplicate Imports

```python
# INCORRECT
import pandas as pd
from datetime import datetime
import pandas  # Duplicate!

# CORRECT
import pandas as pd
from datetime import datetime
```

### Rule 5: Specific Exception Types

```python
# INCORRECT
try:
    from app.domain import something
except:  # CRITICAL ERROR - catches SystemExit, KeyboardInterrupt
    pass

# CORRECT
try:
    from app.domain import something
except ImportError:
    logger.warning("Optional module not available")
```

## Quick Validation Commands

### Fast Import Check (5 seconds)

```bash
# Pyflakes - catches undefined names and unused imports
cd api
./venv/Scripts/python -m pyflakes app/

# Output shows:
# - Unused imports
# - Undefined names
# - Import errors
```

### Comprehensive Validation (30 seconds)

```bash
# Full import validation with circular dependency detection
python scripts/validation/validate_imports.py --root .

# Checks:
# - Import order (PEP 8)
# - Circular dependencies
# - Missing imports
# - Unused imports
# - Lazy imports in functions
```

### Pre-Commit Hook Validation

```bash
# Run before commit
pre-commit run validate-imports --all-files
pre-commit run pyflakes-check --all-files

# Auto-blocks commits with import issues
```

## Common Import Issues

### Issue 1: Circular Dependency

**Symptom:**
```
ImportError: cannot import name 'X' from partially initialized module 'Y'
```

**Example:**
```python
# module_a.py
from module_b import something  # BAD!

# module_b.py
from module_a import other_thing  # Creates circle!
```

**Fix:**
```python
# Move shared code to third module
# shared.py
class SharedThing:
    pass

# module_a.py
from shared import SharedThing

# module_b.py
from shared import SharedThing
```

### Issue 2: Missing Import

**Symptom:**
```
NameError: name 'DataFrame' is not defined
```

**Detection:**
```bash
pyflakes app/domain/export/excel/sheets/calculated_data_sheet.py

# Output:
# app/domain/export/excel/sheets/calculated_data_sheet.py:45:
# undefined name 'DataFrame'
```

**Fix:**
```python
# Add missing import at top
import pandas as pd
from pandas import DataFrame  # or use pd.DataFrame
```

### Issue 3: Lazy Import Performance Hit

**Symptom:** Slow function execution (15-20% overhead)

**Detection:**
```python
# scripts/validation/detect_lazy_imports.py
python scripts/validation/detect_lazy_imports.py

# Finds:
# - Imports inside functions
# - Imports inside loops
# - Repeated imports
```

**Fix:**
```python
# BEFORE (slow)
def create_dashboard(data):
    import pandas as pd  # Called every time!
    return pd.DataFrame(data)

# AFTER (fast)
import pandas as pd  # Once at top

def create_dashboard(data):
    return pd.DataFrame(data)
```

### Issue 4: Import from __init__.py Missing

**Symptom:**
```
ImportError: cannot import name 'SentimentScorer' from 'app.domain.feedback'
```

**Fix:**
```python
# app/domain/feedback/__init__.py
from app.domain.feedback.sentiment_scorer.scorer import SentimentScorer

__all__ = ['SentimentScorer']
```

### Issue 5: Relative vs Absolute Imports

**Project Standard:** Absolute imports only

```python
# INCORRECT - Relative import
from ..constants.colors import ExcelColors

# CORRECT - Absolute import
from app.domain.export.excel.constants.colors import ExcelColors
```

## Dependency Analysis

### View Dependency Tree

```bash
# Install pipdeptree (if not already)
pip install pipdeptree

# View dependencies
pipdeptree

# Output:
# fastapi==0.109.0
#   - pydantic [required: ^2.0.0, installed: 2.5.0]
#   - starlette [required: ==0.35.0, installed: 0.35.0]
```

### Check for Conflicts

```bash
# Check for dependency conflicts
pipdeptree --warn fail

# Output shows conflicts:
# Warning! Conflicting dependencies found:
# - package-a requires package-c>=2.0
# - package-b requires package-c<2.0
```

### Security Audit

```bash
# Check for known vulnerabilities
pip-audit

# Output:
# Found 2 known vulnerabilities in 1 package
# Name    Version  Vulnerability   Fix
# ----    -------  -------------   ---
# urllib3 1.25.0   CVE-2021-33503  Upgrade to 1.26.5
```

## Import Refactoring Patterns

### Pattern 1: Consolidate Common Imports

```python
# BEFORE - Repeated in 10 files
from app.domain.export.excel.constants.colors import (
    ExcelColors,
    TabColors,
    ConditionalFormattingColors
)

# AFTER - Create import helper
# app/domain/export/excel/imports.py
from app.domain.export.excel.constants.colors import (
    ExcelColors,
    TabColors,
    ConditionalFormattingColors
)

__all__ = ['ExcelColors', 'TabColors', 'ConditionalFormattingColors']

# In other files
from app.domain.export.excel.imports import ExcelColors, TabColors
```

### Pattern 2: TYPE_CHECKING for Type Hints

```python
# Avoid circular dependencies in type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.export.excel.sheets import DashboardSheet

def process_sheet(sheet: 'DashboardSheet') -> None:
    # Use string annotation to avoid runtime import
    pass
```

### Pattern 3: Delayed Import for Optional Features

```python
# Import expensive module only when needed
def generate_report():
    # Only import if report generation requested
    from app.domain.export.pdf import PDFGenerator  # Expensive import
    generator = PDFGenerator()
    return generator.create()
```

## Automated Checks

### Pre-Commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pyflakes
        name: pyflakes
        entry: python -m pyflakes
        language: system
        types: [python]
        args: [app/]

      - id: validate-imports
        name: validate-imports
        entry: python scripts/validation/validate_imports.py
        language: system
        pass_filenames: false
```

### CI/CD Integration

```yaml
# .github/workflows/validate-imports.yml
name: Import Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install pyflakes
      - name: Run pyflakes
        run: |
          cd api && python -m pyflakes app/
      - name: Validate imports
        run: |
          python scripts/validation/validate_imports.py --strict
```

## Import Metrics

### Healthy Import Patterns

```
Metric                      | Target | Current | Status
----------------------------|--------|---------|--------
Lazy imports                | 0      | 0       | PASS
Circular dependencies       | 0      | 0       | PASS
Unused imports              | 0      | 3       | WARN
Missing imports             | 0      | 0       | PASS
Import order violations     | 0      | 2       | WARN
Duplicate imports           | 0      | 0       | PASS
```

### Module Import Complexity

```python
# Calculate import complexity score
python scripts/analysis/import_complexity.py

# Output:
# Module: calculated_data_sheet.py
# - Total imports: 25
# - Standard library: 8
# - Third-party: 7
# - Local: 10
# - Complexity score: 42 (threshold: 50)
# - Status: PASS
```

## Best Practices

1. **Import Once**: At module top, not in functions
2. **Organize**: Standard → Third-party → Local
3. **Absolute Paths**: Never use relative imports
4. **Specific Names**: `from module import Class` not `import module`
5. **Type Checking**: Use TYPE_CHECKING for type-only imports
6. **Optional Deps**: Try-except with feature flags
7. **No Wildcards**: Avoid `from module import *`
8. **Clean __init__.py**: Export only what's needed

## Quick Reference

```bash
# Quick check (5 seconds)
cd api && ./venv/Scripts/python -m pyflakes app/

# Full validation (30 seconds)
python scripts/validation/validate_imports.py --root .

# Fix unused imports (auto)
pip install ruff
ruff check api/app --fix

# Dependency tree
pipdeptree

# Security audit
pip-audit

# Pre-commit check
pre-commit run validate-imports --all-files
```

## Success Criteria

Imports are healthy when:
- [ ] No lazy imports (all at top)
- [ ] No circular dependencies
- [ ] No unused imports
- [ ] No missing imports (pyflakes clean)
- [ ] Organized in 3 groups (PEP 8)
- [ ] Absolute imports only
- [ ] Optional dependencies use try-except
- [ ] Pre-commit hooks passing

## References

- [PEP 8 - Imports](https://peps.python.org/pep-0008/#imports)
- [CLAUDE.md](CLAUDE.md) - Import Standards section
- [docs/IMPORT_REFACTORING_PLAN.md](docs/IMPORT_REFACTORING_PLAN.md)
- [scripts/validation/validate_imports.py](scripts/validation/validate_imports.py)

---

**Last Updated:** 2025-11-16
**Status:** Enforced via pre-commit hooks
**Validation Tool:** pyflakes + custom validator
