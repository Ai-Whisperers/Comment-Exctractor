---
description: Run code refactoring checks and quality analysis
model: sonnet
---

# Code Refactoring Analysis

Run comprehensive code quality and refactoring checks.

## Analysis Steps:

1. **Code Quality Check** - Run ruff linting
2. **Type Safety** - Run mypy type checking
3. **Test Coverage** - Check test coverage
4. **Complexity Analysis** - Identify complex functions
5. **Duplication Detection** - Find duplicate code

## Execution:

!bash scripts/testing/test_backend.sh --cov

## What to Review:

- Functions with high cyclomatic complexity
- Modules lacking test coverage
- Code duplication opportunities
- Type hint completeness
- PEP 8 compliance

## Next Steps:

1. Address critical linting issues
2. Add type hints where missing
3. Refactor complex functions
4. Increase test coverage
5. Remove code duplication

Use this before major refactoring to establish baseline metrics.
