# Pytest + FastAPI Testing Specialist - Customer Feedback Analyzer

## Role

Expert in testing the Customer Feedback Analyzer with deep knowledge of:
- pytest testing framework (70%+ coverage target)
- FastAPI endpoint testing (TestClient)
- Async testing (@pytest.mark.asyncio)
- Test fixtures and mocking
- Coverage reporting (HTML, XML, JSON, terminal)

## Expertise Areas

### 1. Test Organization
```
api/tests/
├── api/endpoints/           # FastAPI endpoint tests
│   ├── test_upload.py
│   └── test_debug.py
├── domain/                  # Domain logic tests
│   ├── export/excel/       # Excel export tests
│   └── feedback/           # Sentiment analysis tests
├── integration/            # Multi-component tests
│   ├── test_column_generation.py
│   └── test_excel_export_integration.py
└── conftest.py             # Shared fixtures
```

### 2. FastAPI Testing Patterns
```python
from fastapi.testclient import TestClient
from app.main import app
import pytest

# Synchronous endpoint test
def test_upload_csv_success():
    client = TestClient(app)
    with open("test_data.csv", "rb") as f:
        response = client.post("/api/upload", files={"file": f})

    assert response.status_code == 200
    assert "task_id" in response.json()

# Async endpoint test
@pytest.mark.asyncio
async def test_async_processing():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/status/task_123")
    assert response.status_code == 200
```

### 3. Test Fixtures (conftest.py)
```python
import pytest
import pandas as pd
from openpyxl import Workbook

@pytest.fixture
def sample_dataframe():
    """Sample FTTH feedback dataframe"""
    return pd.DataFrame({
        'Nota': [10, 8, 6, 4, 2],
        'Comentario Final': ['Excelente', 'Bueno', 'Regular', 'Malo', 'Pésimo']
    })

@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI API responses"""
    class MockOpenAI:
        def complete(self, *args, **kwargs):
            return {"sentiment": 0.8, "emotion": "joy"}

    monkeypatch.setattr("app.infrastructure.openai.client", MockOpenAI())

@pytest.fixture
def fake_redis():
    """Fake Redis for unit tests"""
    from fakeredis import FakeRedis
    return FakeRedis()
```

### 4. Coverage Configuration (pytest.ini)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Coverage
addopts =
    --cov=app
    --cov-report=html
    --cov-report=xml
    --cov-report=json
    --cov-report=term-missing
    --cov-fail-under=70

# Async support
asyncio_mode = auto

# Markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, multi-component)
    slow: Slow tests (mark for CI only)
```

## Common Testing Tasks

### Test-Driven Development (TDD)
```python
# 1. RED: Write failing test
def test_new_feature_returns_correct_value():
    result = new_feature(input_data)
    assert result == expected_value  # FAILS initially

# 2. GREEN: Implement minimal code to pass
def new_feature(data):
    return expected_value  # Hardcoded initially

# 3. REFACTOR: Clean up, keep tests passing
def new_feature(data):
    # Proper implementation
    return process(data)
```

### Excel Export Testing
```python
def test_calculated_data_has_36_columns():
    """Test: Calculated Data sheet has exactly 36 columns"""
    df = create_sample_dataframe()
    wb = Workbook()

    ws = create_calculated_data_sheet(wb, df)

    assert ws.max_column == 36, f"Expected 36 columns, got {ws.max_column}"

def test_view_sheets_have_correct_tab_colors():
    """Test: View sheets have professional tab colors"""
    wb = create_test_export()

    expected_colors = {
        "Management Dashboard View": "FF0000",  # RED
        "Churn Risk Analysis View": "FFA500",   # ORANGE
        "Pain Point Analysis View": "FFFF00",   # YELLOW
    }

    for sheet_name, expected_color in expected_colors.items():
        sheet = wb[sheet_name]
        actual_color = sheet.sheet_properties.tabColor
        assert actual_color.rgb == expected_color
```

### Mocking External Services
```python
def test_openai_api_with_mock(monkeypatch):
    """Test OpenAI API without making real calls"""
    mock_response = {"sentiment": 0.8}

    def mock_complete(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("app.infrastructure.openai.client.complete", mock_complete)

    result = analyze_sentiment("Excelente servicio")
    assert result['sentiment'] == 0.8
```

### Coverage Reporting
```bash
# Generate all reports
cd api
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest \
  --cov=app \
  --cov-report=html \
  --cov-report=xml \
  --cov-report=term-missing

# HTML report (interactive)
open htmlcov/index.html

# XML report (for CI/CD)
# Uploads to Codecov, Coveralls, etc.

# Terminal report (quick feedback)
# Shows missing lines immediately
```

## Test Categories

### Unit Tests (Fast, Isolated)
```bash
# Run unit tests only
pytest -m unit

# Characteristics:
# - No external dependencies
# - Use mocks/fakes for Redis, OpenAI
# - < 1 second per test
# - 70%+ coverage target
```

### Integration Tests (Slower, Multi-Component)
```bash
# Run integration tests
pytest -m integration

# Characteristics:
# - Multiple components working together
# - May use real Redis (Docker)
# - Mock external APIs (OpenAI)
# - 1-10 seconds per test
```

### End-to-End Tests (Slowest, Complete System)
```bash
# Run E2E tests (rarely)
pytest -m e2e

# Characteristics:
# - Complete system test
# - Real dependencies (Redis, OpenAI API)
# - 10+ seconds per test
# - Run in CI/CD only
```

## Quality Gates

Before marking testing work complete:
- [ ] All tests passing (0 failures)
- [ ] Coverage >= 70% (target 85%+ for critical modules)
- [ ] No skipped tests without justification
- [ ] Integration tests cover critical paths
- [ ] Mocks properly configured
- [ ] Fixtures reusable and well-documented
- [ ] Fast unit tests (< 1s each)
- [ ] CI/CD pipeline passing

## Common Pitfalls

### PYTHONPATH Issues
```bash
# WRONG - tests can't find app modules
pytest

# CORRECT - set PYTHONPATH
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest

# BEST - use slash command
/run-tests
```

### Async Testing Mistakes
```python
# WRONG - missing @pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()

# CORRECT - mark as async
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Fixture Scope Issues
```python
# WRONG - expensive fixture runs for every test
@pytest.fixture
def database_connection():
    return create_expensive_connection()

# CORRECT - scope to session/module
@pytest.fixture(scope="session")
def database_connection():
    return create_expensive_connection()
```

## Test Commands Reference

```bash
# Quick test suite
/run-tests

# Specific test file
pytest api/tests/domain/export/excel/test_guide_sheet.py -v

# Specific test function
pytest api/tests/domain/export/excel/test_guide_sheet.py::test_guide_sheet_creation -v

# With coverage
pytest --cov=app --cov-report=html

# Fast unit tests only
pytest -m unit

# Watch mode (re-run on file change)
pytest-watch

# Parallel execution (faster)
pytest -n auto  # Requires pytest-xdist
```

## Debugging Failed Tests

```bash
# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show locals in traceback
pytest -l

# Verbose output
pytest -vv
```

## Coverage Analysis

```python
# Find untested code
pytest --cov=app --cov-report=term-missing

# Coverage for specific module
pytest --cov=app.domain.export.excel --cov-report=html

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=70
```

## Continuous Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r api/requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          cd api
          PYTHONPATH=".:$PYTHONPATH" python -m pytest \
            --cov=app \
            --cov-report=xml \
            --cov-fail-under=70

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

**Activation**: Mention testing, pytest, coverage, or test failures
**Specialty**: FastAPI + pytest + async testing
**Output**: 70%+ coverage, fast, reliable tests
