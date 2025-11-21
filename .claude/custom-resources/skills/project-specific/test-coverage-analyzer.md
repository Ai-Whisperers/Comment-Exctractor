# Test Coverage Analyzer Skill

Analyze test coverage and identify gaps in the Customer Feedback Analyzer test suite.

## Metadata

- **Name**: Test Coverage Analyzer
- **Category**: Testing & Quality Assurance
- **Activation**: Automatic when coverage mentioned
- **Model**: Haiku (fast analysis) or Sonnet (deep analysis)
- **Token Cost**: ~800 tokens

## When to Activate

Trigger this skill when user mentions:
- "Check test coverage"
- "Coverage report"
- "What's not tested"
- "Missing tests"
- "Test gaps"
- "Improve coverage"
- "Add tests for..."

## Current Coverage Status

### Overall Target

- **Current:** 72% (as of v3.8.0)
- **Target:** 85%
- **Minimum:** 70%

### Module Coverage (from pytest.ini)

```
Minimum coverage threshold: 70%
Coverage reports: HTML + JSON + XML + Terminal
Measured against: api/app/
```

## Coverage Analysis Commands

### Quick Coverage Check (30 seconds)

```bash
/run-tests

# Shows coverage summary at end
# Format: HTML report in htmlcov/index.html
```

### Detailed Coverage Report (2 minutes)

```bash
cd api
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest --cov=app --cov-report=html --cov-report=term-missing

# Open: htmlcov/index.html for interactive report
# Shows: Line-by-line coverage, missing lines highlighted
```

### Module-Specific Coverage

```bash
# Sentiment analysis
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest --cov=app/domain/feedback/sentiment_scorer tests/domain/feedback/

# Excel export
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest --cov=app/domain/export/excel tests/domain/export/excel/

# Upload service
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest --cov=app/domain/upload tests/domain/upload/
```

## Critical Modules to Test

### Priority 1: Core Business Logic (Target: 90%+)

1. **Sentiment Analysis** (app/domain/feedback/sentiment_scorer/)
   - Current: ~85%
   - Missing: Edge cases for optimized analyzer
   - Tests: api/tests/domain/feedback/

2. **Excel Export** (app/domain/export/excel/)
   - Current: ~78%
   - Missing: View sheet error handling
   - Tests: api/tests/domain/export/excel/

3. **Calculated Metrics** (app/domain/feedback/metrics/)
   - Current: ~80%
   - Missing: Boundary conditions for priority score
   - Tests: api/tests/domain/feedback/

### Priority 2: Infrastructure (Target: 80%+)

4. **Upload Service** (app/domain/upload/)
   - Current: ~72%
   - Missing: Large file handling, corruption scenarios
   - Tests: api/tests/domain/upload/

5. **Error Handling** (app/infrastructure/observability/errors/)
   - Current: ~68%
   - Missing: Circuit breaker edge cases
   - Tests: api/tests/infrastructure/

### Priority 3: API Layer (Target: 75%+)

6. **Upload Endpoint** (app/api/endpoints/upload/)
   - Current: ~75%
   - Missing: Concurrent upload scenarios
   - Tests: api/tests/api/endpoints/

## Coverage Gap Analysis

### Identify Uncovered Code

```python
# Run coverage and generate report
pytest --cov=app --cov-report=term-missing

# Look for:
# - Lines with "!" (not executed)
# - Functions with 0% coverage
# - Branches not taken
```

### Common Uncovered Areas

1. **Error Handling Branches**
   ```python
   # Often uncovered:
   except Exception as e:
       logger.error("Critical error", exc_info=True)
       # This path not tested
   ```

2. **Edge Cases**
   ```python
   # Often uncovered:
   if user_score <= 0:  # Rarely tested
       return "VERY_LOW"
   ```

3. **Async Error Paths**
   ```python
   # Often uncovered:
   try:
       result = await openai_client.complete(...)
   except TimeoutError:  # Not tested
       pass
   ```

4. **Optional Features**
   ```python
   # Often uncovered:
   if PSUTIL_AVAILABLE:  # Optional dependency
       memory = psutil.virtual_memory()
   ```

## Test Gap Identification

### Automated Gap Detection

```python
# Run coverage and identify gaps
python scripts/testing/identify_coverage_gaps.py

# Output:
# Module: sentiment_scorer
# Coverage: 85%
# Missing:
#   - Line 142-145: Error handling for invalid sentiment
#   - Line 201-203: Cache miss scenario
#   - Line 278: Edge case for empty comment
```

### Manual Gap Review

1. **Read coverage report**: htmlcov/index.html
2. **Sort by coverage**: Lowest first
3. **Identify patterns**: What type of code is uncovered?
4. **Prioritize**: Business logic > infrastructure > utilities

## Writing Tests for Gaps

### Template: Missing Error Handler

```python
# Uncovered code
try:
    result = process_data(data)
except ValueError as e:
    logger.error("Invalid data", error=str(e))  # Not tested
    return None

# Test to add
def test_process_data_invalid_input():
    """Test error handling for invalid data."""
    with pytest.raises(ValueError):
        process_data(invalid_data)

    # Or if error is caught:
    result = process_data(invalid_data)
    assert result is None
    # Verify logger.error was called
```

### Template: Missing Edge Case

```python
# Uncovered code
if user_score <= 0:  # Not tested
    return "VERY_LOW"

# Test to add
def test_sentiment_category_very_low_score():
    """Test sentiment category for score <= 0."""
    assert get_sentiment_category(0) == "VERY_LOW"
    assert get_sentiment_category(-1) == "VERY_LOW"
```

### Template: Missing Branch

```python
# Uncovered branch
if has_pain_point and churn_risk > 70:
    return "URGENT"  # Tested
else:
    return "MEDIUM"  # Not tested

# Test to add
def test_priority_score_no_pain_point():
    """Test priority when no pain point."""
    score = calculate_priority(
        has_pain_point=False,
        churn_risk=80
    )
    assert score == "MEDIUM"
```

## Coverage Improvement Workflow

### Step 1: Baseline Measurement

```bash
# Measure current coverage
/run-tests

# Note the percentage: e.g., 72%
```

### Step 2: Identify Top 5 Gaps

```python
# Run gap analysis
python scripts/testing/identify_coverage_gaps.py

# Focus on:
# 1. Lowest coverage modules
# 2. Critical business logic
# 3. Recently changed code
# 4. Bug-prone areas
# 5. High-impact features
```

### Step 3: Write Tests

```bash
# For each gap, write test
# Example: sentiment_scorer missing edge case

# Create test file (if not exists)
touch api/tests/domain/feedback/test_sentiment_edge_cases.py

# Write test
# Run test
pytest api/tests/domain/feedback/test_sentiment_edge_cases.py -v
```

### Step 4: Verify Improvement

```bash
# Re-run coverage
/run-tests

# Check new percentage: e.g., 72% → 75%
# Commit if improved
```

### Step 5: Iterate

Repeat until 85% coverage achieved.

## Integration Tests vs Unit Tests

### Unit Tests (Fast, Isolated)

- Test single function/method
- Mock dependencies
- Fast execution (<1s per test)
- 80%+ of test suite

```python
# Example unit test
def test_calculate_priority_score():
    score = calculate_priority(
        review_priority=80,
        churn_risk=60
    )
    assert score == "URGENT"
```

### Integration Tests (Slower, End-to-End)

- Test multiple components
- Real dependencies (or close to real)
- Slower execution (1-10s per test)
- 20% of test suite

```python
# Example integration test
def test_excel_export_full_pipeline():
    # Upload file
    # Process with AI
    # Generate Excel
    # Validate output
    assert all_columns_present(excel_file)
```

## Pre-Commit Coverage Hook

### Add to .claude/hooks/

```python
# pre_commit_coverage.py

def check_coverage():
    """Ensure coverage doesn't decrease."""
    result = run_pytest_with_coverage()
    current = extract_coverage(result)

    if current < MINIMUM_COVERAGE:
        print(f"Coverage {current}% below minimum {MINIMUM_COVERAGE}%")
        return False

    return True
```

### Add to settings.local.json

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/pre_commit_coverage.py",
            "timeout": 60000
          }
        ]
      }
    ]
  }
}
```

## Coverage Metrics Dashboard

### Current Status

```
Module                          | Coverage | Target | Gap
--------------------------------|----------|--------|-----
sentiment_scorer/               | 85%      | 90%    | 5%
export/excel/                   | 78%      | 85%    | 7%
calculated_metrics/             | 80%      | 85%    | 5%
upload/                         | 72%      | 80%    | 8%
errors/                         | 68%      | 80%    | 12%
api/endpoints/upload/           | 75%      | 75%    | 0%
--------------------------------|----------|--------|-----
Overall                         | 72%      | 85%    | 13%
```

### Weekly Tracking

```
Week        | Coverage | Change | Tests Added
------------|----------|--------|-------------
2025-11-09  | 70%      | +2%    | 15 tests
2025-11-16  | 72%      | +2%    | 12 tests
Target      | 85%      | -      | ~100 tests needed
```

## Best Practices

1. **Test First**: Write test before fixing gaps
2. **One Test, One Assertion**: Keep tests focused
3. **Descriptive Names**: `test_sentiment_category_edge_case_zero_score()`
4. **Fast Tests**: Aim for <100ms per unit test
5. **Isolated Tests**: No dependencies between tests
6. **Clear Arrange-Act-Assert**: Structure tests clearly

## Common Pitfalls

1. **Testing Implementation, Not Behavior**
   - Bad: Test internal variable names
   - Good: Test function outputs

2. **Mocking Too Much**
   - Bad: Mock everything
   - Good: Mock external dependencies only

3. **Ignoring Edge Cases**
   - Bad: Only test happy path
   - Good: Test boundaries, errors, edge cases

4. **Slow Tests**
   - Bad: Integration tests for everything
   - Good: Fast unit tests, selective integration

## References

- [api/pytest.ini](api/pytest.ini) - Coverage configuration
- [api/tests/conftest.py](api/tests/conftest.py) - Test fixtures
- [CLAUDE.md](CLAUDE.md) - Testing section

## Quick Commands

```bash
# Full coverage report
/run-tests

# Module-specific
/test-excel

# Gap analysis
python scripts/testing/identify_coverage_gaps.py

# HTML report
open api/htmlcov/index.html
```

---

**Last Updated:** 2025-11-16
**Current Coverage:** 72%
**Target:** 85%
**Status:** In progress
