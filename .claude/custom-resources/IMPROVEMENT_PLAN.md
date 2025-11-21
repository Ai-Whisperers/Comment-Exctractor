# Customer Feedback Analyzer - Resource Improvement Plan

**Created**: 2025-11-16
**Purpose**: Tailored customization roadmap for 247 Claude Code resources
**Project**: Customer Feedback Analyzer (FastAPI + React + OpenAI)

---

## Executive Summary

**Available Resources**: 247 professional templates
- 122 skills across 20 categories
- 8 hooks (all lifecycle events)
- 63 commands
- 49 agents
- 5 meta-guides

**Customization Strategy**: 3-phase implementation
- Phase 1 (Week 1): 6 core skills - Quality & Testing
- Phase 2 (Week 2): 5 automation hooks - Workflow efficiency
- Phase 3 (Week 3): 8 custom commands - Project-specific workflows

**Expected Impact**:
- 50+ hours/year time savings
- 70% -> 85%+ test coverage
- Zero Excel export bugs
- Automated code quality enforcement

---

## Project Context Analysis

### Current Tech Stack
- Backend: FastAPI + Celery + Redis
- Frontend: React 18.3 + TypeScript
- AI: OpenAI GPT-4o-mini (87% cost optimized)
- Data: Pandas + Excel export (openpyxl)
- Testing: pytest (70% coverage target)
- Deployment: Render.com + Docker

### Current Pain Points (from CLAUDE.md)
1. Excel export validation (manual, 15 min -> should be 30 sec)
2. Import quality issues (lazy imports, PEP 8 violations)
3. Test coverage gaps (70% current, want 85%+)
4. Manual code review overhead
5. Repetitive debugging without systematic approach

### Project Strengths
- Strong documentation culture (33% of AI requests)
- High testing focus (31% of AI requests)
- Data-driven optimization (84 conversations analyzed)
- Modern architecture (dependency injection, modular design)

---

## Phase 1: Core Quality Skills (Week 1, 6 hours)

### 1.1 Excel Export Validator (Priority: CRITICAL)

**Source Template**: `skills/excel/xlsx-processing-anthropic.md`

**Why Critical**:
- Excel export is core feature (v3.9.0 with 7 specialized sheets)
- Currently manual validation takes 15 minutes
- Zero formula errors required (customer-facing deliverable)

**Customizations Needed**:

```markdown
---
name: excel-export-validator
description: Validates Customer Feedback Analyzer Excel exports with 7 view sheets, 36 columns, and conditional formatting. Use when checking Excel files, verifying export quality, debugging Excel generation, or before releasing new versions.
---

# Excel Export Validator - Customer Feedback Analyzer

## Project-Specific Validation

### 1. Sheet Structure (7 View Sheets Required)
- Management Dashboard View (RED tab, Priority >= 60 OR Churn >= 40)
- Churn Risk Analysis View (ORANGE tab, Churn >= 40 OR Exit Threat)
- Pain Point Analysis View (YELLOW tab, Has pain point)
- Sentiment Analysis View (BLUE tab, No filter)
- Quality Control View (PURPLE tab, Needs review OR quality issues)
- Duplicate Analysis View (GRAY tab, Is duplicate)
- Calculated Data (End of workbook, complete 36-column dataset)

### 2. Column Schema (36 Columns in Calculated Data)
**GROUP 1: Primary Review (10 columns)**
- User Score, Customer Comment, AI Sentiment, Analysis Score, Score Source
- Sentiment Category, Emotion, Churn Risk, Review Priority Score
- Pain Point Category (Primary)

**GROUP 2: Secondary Analysis (7 columns)**
- Pain Point Category (Secondary), Pain Point Keywords
- Sentiment Score Alignment, Actionability Score, Word Count
- Has Deep Insights, Deep Insights JSON

**GROUP 3: Duplicate Detection (5 columns)**
- Is Duplicate, Duplicate Count, Duplicate Group ID
- First Occurrence ID, Is First Occurrence

**GROUP 4: Quality Control (3 columns)**
- Quality Flags, Analysis Tier, Problemas Detectados

**GROUP 5: AI Correction Details (4 columns)**
- Original User Score, Sentiment Score (Before Check)
- Discrepancy Flag, Discrepancy Explanation

**GROUP 6: Technical Scores (7 columns)**
- Sentiment Score (GPT-4o-mini), Confidence Score
- [5 additional technical metrics]

### 3. Tab Colors (Professional Color Scheme)
- RED: Management Dashboard (urgent priority)
- ORANGE: Churn Risk (customer retention)
- YELLOW: Pain Points (product improvement)
- BLUE: Sentiment (trends analysis)
- PURPLE: Quality Control (QA validation)
- GRAY: Duplicates (data cleanliness)

### 4. Conditional Formatting Rules
- Review Priority Score: Red (80-100), Yellow (60-80), Green (40-60)
- Churn Risk: Color-coded indicators
- Sentiment discrepancy: Highlight large gaps

### 5. Verification Commands
```bash
# Run export validator
cd api
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest api/tests/domain/export/excel/ -v

# Integration test (full export)
cd api/tests/integration
python test_excel_export_integration.py

# Visual inspection checklist
# 1. All 7 view sheets present
# 2. Tab colors correct (RED/ORANGE/YELLOW/BLUE/PURPLE/GRAY)
# 3. Conditional formatting applied
# 4. No #REF! or #VALUE! errors
# 5. Formulas calculate correctly (if any)
# 6. Column count = 36 in Calculated Data
```

## When NOT to Use
- Skip for CSV exports (different validator)
- Skip for internal Excel files (only for customer-facing exports)

## Red Flags
- Any sheet missing from the 7 required
- Wrong tab colors
- Column count != 36 in Calculated Data
- Missing conditional formatting
- Formula errors
```

**Implementation Time**: 1 hour
**Expected Savings**: 14.5 min/export × 20 exports/month = 4.8 hours/month

---

### 1.2 Systematic Testing/TDD (Priority: HIGH)

**Source Template**: `skills/testing/tdd-superpowers.md`

**Why High Priority**:
- Current coverage: 70% (want 85%+)
- Strong testing culture (31% of AI requests)
- Prevent regressions in complex domain logic

**Customizations Needed**:

```markdown
---
name: systematic-testing
description: Enforces test-driven development for Customer Feedback Analyzer. Use when implementing features, fixing bugs, adding functionality, or refactoring. Requires pytest tests before code, 70% minimum coverage, type hints, and PEP 8 compliance.
---

# Test-Driven Development - Customer Feedback Analyzer

## The Iron Law
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

## Project-Specific Test Patterns

### 1. FastAPI Endpoint Testing
```python
# CORRECT Pattern (write test first)
# File: api/tests/api/endpoints/test_upload.py

from fastapi.testclient import TestClient
import pytest

@pytest.mark.asyncio
async def test_upload_ftth_dataset_success():
    """Test: FTTH dataset upload returns task_id"""
    # ARRANGE
    client = TestClient(app)
    file_path = "api/tests/data/ftth_846_reviews.csv"

    # ACT
    with open(file_path, 'rb') as f:
        response = client.post("/api/upload", files={"file": f})

    # ASSERT
    assert response.status_code == 200
    assert "task_id" in response.json()

# NOW implement the endpoint to make test pass
```

### 2. Domain Logic Testing (Sentiment Analysis)
```python
# File: api/tests/domain/feedback/test_sentiment_scorer.py

def test_spanish_sentiment_positive():
    """Test: Spanish positive feedback scores >= 0.5"""
    scorer = SentimentScorer(language="es")

    # Test data from real FTTH feedback
    comment = "Excelente servicio, muy rápido y confiable"

    score = scorer.score_comment(comment)

    assert score >= 0.5, "Positive sentiment should be >= 0.5"
    assert score <= 1.0, "Sentiment score must be in range [0, 1]"
```

### 3. Excel Export Testing
```python
# File: api/tests/domain/export/excel/test_calculated_data_sheet.py

def test_calculated_data_has_36_columns():
    """Test: Calculated Data sheet has exactly 36 columns"""
    # ARRANGE
    df = create_test_dataframe()
    wb = Workbook()

    # ACT
    ws = create_calculated_data_sheet(wb, df)

    # ASSERT
    assert ws.max_column == 36, f"Expected 36 columns, got {ws.max_column}"
```

### 4. Coverage Requirements
```bash
# Minimum 70% coverage (from pytest.ini)
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest --cov=app --cov-report=html

# Target 85%+ for critical modules
--cov-fail-under=85 api/app/domain/export/excel/
--cov-fail-under=85 api/app/domain/feedback/
```

### 5. Pre-commit Testing
```bash
# Run before every commit
bash scripts/testing/test_backend.sh --cov

# Or use slash command
/run-tests
```

## RED-GREEN-REFACTOR Cycle

1. RED: Write failing test
2. GREEN: Minimal code to pass
3. REFACTOR: Clean up, maintain coverage
4. REPEAT

## When to Use
- Before implementing ANY new feature
- Before fixing ANY bug
- Before refactoring
- During code review (verify tests exist)

## Red Flags
- Test written AFTER implementation
- Test that never failed (not testing anything)
- Coverage drop below 70%
- Missing tests for bug fixes
```

**Implementation Time**: 1.5 hours
**Expected Impact**: 70% -> 85% coverage, 60-70% fewer bugs

---

### 1.3 Systematic Debugging (Priority: HIGH)

**Source Template**: `skills/debugging/systematic-debugging-superpowers.md`

**Why High Priority**:
- 80 debugging requests in 84 conversations (17%)
- Complex multi-component system (FastAPI + Celery + Redis + OpenAI)
- Reduce debugging time by 50%

**Customizations Needed**:

```markdown
---
name: systematic-debugging
description: Systematic debugging for Customer Feedback Analyzer multi-component system. Use when debugging errors, investigating bugs, tracking issues across FastAPI/Celery/Redis/OpenAI, or when 3+ fixes fail (architectural problem).
---

# Systematic Debugging - Customer Feedback Analyzer

## The 4-Phase Framework (MANDATORY)

### Phase 1: Root Cause Investigation (NO FIXES YET)
```bash
# 1. Component Identification
# - FastAPI endpoint? (api/app/api/endpoints/)
# - Domain logic? (api/app/domain/)
# - Celery worker? (api/app/infrastructure/celery/)
# - Redis cache? (api/app/infrastructure/cache/)
# - OpenAI API? (api/app/infrastructure/openai/)
# - Excel export? (api/app/domain/export/excel/)

# 2. Structured Logging Analysis
cd api
grep -r "ERROR" logs/ | tail -50

# 3. Stack Trace Review
# Check full stack trace with exc_info=True
```

### Phase 2: Pattern Analysis
```bash
# Is this error:
# - Intermittent? (OpenAI timeout, Redis connection)
# - Consistent? (Logic bug, schema issue)
# - Data-dependent? (Specific CSV format, edge case)
# - Environment-dependent? (Windows vs production)

# Check error patterns
grep "YourError" logs/ | wc -l
```

### Phase 3: Hypothesis Testing
```python
# Test hypothesis with isolated unit test
# File: api/tests/debug/test_hypothesis.py

def test_hypothesis_excel_export_fails_on_empty_df():
    """Hypothesis: Excel export fails when dataframe is empty"""
    df = pd.DataFrame()  # Empty dataframe

    with pytest.raises(ValueError, match="Empty dataframe"):
        export_to_excel(df)
```

### Phase 4: Implementation
- Fix root cause (not symptoms)
- Add test to prevent regression
- Update documentation if needed

## Project-Specific Debugging Patterns

### 1. OpenAI API Errors
```bash
# Check rate limits and circuit breaker
grep "RateLimitError" logs/
grep "CircuitBreakerOpenError" logs/

# Verify API key and quota
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### 2. Celery Worker Issues
```bash
# Check worker status
docker-compose ps celery-worker

# Check task queue
redis-cli LLEN celery

# Check worker logs
docker-compose logs celery-worker --tail=100
```

### 3. Excel Export Failures
```python
# Common causes:
# 1. Missing columns in dataframe
# 2. Wrong data types
# 3. Conditional formatting errors
# 4. Tab color issues

# Debug with minimal test
pytest api/tests/domain/export/excel/test_guide_sheet.py -v
```

### 4. Import Errors
```bash
# Quick import validation (5 seconds)
cd api
./venv/Scripts/python -m pyflakes app/

# Full validation
python scripts/validation/validate_imports.py --root . --strict
```

## When to STOP and Rethink Architecture
- 3+ different fixes attempted, all failed
- Same error keeps returning
- Workarounds piling up

## Red Flags
- Fixing symptoms instead of root cause
- Skipping Phase 1 (investigation)
- No test added after bug fix
- Silent exception catching (bare except:)
```

**Implementation Time**: 1 hour
**Expected Impact**: 50% faster debugging, fewer recurring bugs

---

### 1.4 Import Quality Enforcer (Priority: MEDIUM)

**Source Template**: `skills/code-quality/verification-before-completion-superpowers.md`

**Why Medium Priority**:
- Recent import refactoring (November 2025)
- PEP 8 compliance required
- Prevent lazy imports

**Customizations Needed**:

```markdown
---
name: import-quality-enforcer
description: Validates Python imports follow PEP 8 standards for Customer Feedback Analyzer. Use when checking code quality, before commits, during refactoring, or reviewing PRs. Detects lazy imports, circular dependencies, missing modules.
---

# Import Quality Enforcer - Customer Feedback Analyzer

## The Iron Law
```
ALL IMPORTS AT TOP OF FILE (PEP 8)
NO LAZY IMPORTS (except optional dependencies)
```

## Quick Validation (5 seconds)
```bash
cd api
./venv/Scripts/python -m pyflakes app/
```

## Import Organization Standard

```python
# CORRECT Import Organization
# File: api/app/domain/export/excel/service/export_service.py

# 1. Standard library imports
import asyncio
import os
from datetime import datetime
from typing import Optional, List, Dict

# 2. Third-party imports
import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.workbook import Workbook

# 3. Local application imports
from app.domain.export.excel.constants.colors import ExcelColors
from app.shared.logging import get_logger

logger = get_logger(__name__)
```

## Common Violations

### 1. Lazy Imports (BAD)
```python
# BAD - Import inside function
def create_dashboard_sheet(wb, df):
    from openpyxl.chart import PieChart  # WRONG!
    ...
```

### 2. Duplicate Imports (BAD)
```python
# BAD - Imported twice
from app.domain.feedback import SentimentScorer
...
from app.domain.feedback import SentimentScorer  # Duplicate!
```

### 3. Circular Dependencies (BAD)
```bash
# Detect circular imports
python scripts/validation/validate_imports.py --root . --strict
```

## Automated Fixes

### Using ruff (recommended)
```bash
pip install ruff
ruff check api/app api/tests --fix
```

### Using isort
```bash
isort api/app api/tests
```

## Pre-commit Hook Integration
```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
cd api
./venv/Scripts/python -m pyflakes app/
if [ $? -ne 0 ]; then
    echo "Import validation failed. Fix imports before committing."
    exit 1
fi
```

## When to Use
- Before every commit
- During code review
- After refactoring
- When adding new modules

## Red Flags
- Imports inside functions (lazy loading)
- Missing imports (NameError at runtime)
- Circular import errors
- Wildcard imports (from module import *)
```

**Implementation Time**: 45 min
**Expected Impact**: Zero import errors, 15-20% performance improvement

---

### 1.5 Verification Before Completion (Priority: HIGH)

**Source Template**: `skills/code-quality/verification-before-completion-superpowers.md`

**Why High Priority**:
- Prevent incomplete tasks
- Ensure quality gates
- Reduce back-and-forth

**Customizations Needed**:

```markdown
---
name: verification-before-completion
description: Quality gates before marking tasks complete for Customer Feedback Analyzer. Use before finishing features, closing tickets, marking todos complete, or submitting PRs.
---

# Verification Before Completion - Customer Feedback Analyzer

## The Iron Law
```
NO TASK IS COMPLETE WITHOUT:
1. Tests passing (70%+ coverage)
2. Type hints added
3. Imports at top of file
4. Documentation updated
5. No lint errors
```

## Quality Gates Checklist

### 1. Code Quality
```bash
# Run all quality checks
cd api

# Type checking
mypy app/config/analysis_thresholds.py --config-file mypy.ini

# Import validation
./venv/Scripts/python -m pyflakes app/

# Lint check
ruff check app/ tests/
```

### 2. Testing
```bash
# Full test suite
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest --cov=app --cov-report=html

# Coverage requirement: 70% minimum
# Target: 85%+ for critical modules
```

### 3. Documentation
- CLAUDE.md updated (if architecture changed)
- Docstrings added (Google style)
- README updated (if public API changed)
- CHANGELOG.md updated (for releases)

### 4. Excel Export Specific
```bash
# If Excel export modified:
pytest api/tests/domain/export/excel/ -v
pytest api/tests/integration/test_column_generation.py -v

# Visual check:
# - 7 view sheets present
# - 36 columns in Calculated Data
# - Tab colors correct
# - Conditional formatting applied
```

### 5. Repository Organization
```bash
# Verify repo structure
bash scripts/development/check_repo_organization.sh
```

## Before Marking Todo Complete

```python
# TodoWrite - Mark ONLY when ALL criteria met:
{
  "content": "Implement Excel export validator",
  "status": "completed",  # ONLY if ALL quality gates passed
  "activeForm": "Implementing Excel export validator"
}
```

## Red Flags (DO NOT MARK COMPLETE)
- Tests failing
- Coverage dropped
- Import errors present
- Type errors in mypy
- Documentation missing
- Repository check fails

## When to Use
- Before marking todos as completed
- Before closing GitHub issues
- Before submitting pull requests
- Before deployments
```

**Implementation Time**: 30 min
**Expected Impact**: Zero incomplete tasks, higher first-time quality

---

### 1.6 Code Review Workflow (Priority: MEDIUM)

**Source Template**: `skills/code-quality/code-review-superpowers.md` (if exists)

**Why Medium Priority**:
- Improve PR quality
- Catch issues early
- Knowledge sharing

**Customizations Needed**:

```markdown
---
name: code-review-workflow
description: Systematic code review for Customer Feedback Analyzer pull requests. Use when reviewing PRs, checking diffs, validating changes, or mentoring team members.
---

# Code Review Workflow - Customer Feedback Analyzer

## Review Checklist

### 1. Architecture Compliance
- Clean architecture layers respected (API -> Domain -> Infrastructure)
- No business logic in API layer
- No infrastructure code in domain layer
- Dependency injection used correctly

### 2. Code Quality
```bash
# Run automated checks
cd api
mypy app/ --config-file mypy.ini
./venv/Scripts/python -m pyflakes app/
ruff check app/
```

### 3. Testing
- All new code has tests
- Coverage >= 70% (target 85%+)
- Tests follow AAA pattern (Arrange-Act-Assert)
- No skipped tests without justification

### 4. Documentation
- Docstrings for public functions
- CLAUDE.md updated if needed
- Inline comments for complex logic
- README updated for breaking changes

### 5. Excel Export Changes
- 7 view sheets still present
- 36 columns in Calculated Data
- Tab colors correct
- Integration test passing

### 6. Security
- No credentials committed
- No SQL injection vulnerabilities
- Input validation present
- Error messages don't leak sensitive data

### 7. Performance
- No N+1 queries
- Batch operations used
- Cache strategy appropriate
- No unnecessary API calls

## Common Issues to Flag

1. Bare except clauses (use specific exceptions)
2. Lazy imports (imports inside functions)
3. Magic numbers (use constants from analysis_thresholds.py)
4. Missing type hints
5. Poor variable names
6. Commented-out code
7. TODO comments without tickets

## When to Request Changes
- Any quality gate fails
- Tests missing for new code
- Architecture violated
- Security issues present

## When to Approve
- All checks pass
- Documentation complete
- No blocking issues
- Minor issues noted but not blocking
```

**Implementation Time**: 1 hour
**Expected Impact**: Higher PR quality, fewer production bugs

---

## Phase 1 Summary

**Total Time**: 6 hours
**Skills Created**: 6
**Expected Impact**:
- Excel validation: 15 min -> 30 sec (4.8 hours/month saved)
- Test coverage: 70% -> 85%+ (60-70% fewer bugs)
- Debug time: 50% reduction
- Import errors: Zero
- Incomplete tasks: Zero
- Code review efficiency: 30% faster

---

## Phase 2: Automation Hooks (Week 2, 4 hours)

### 2.1 Auto-Format Python (post_tool_use.py)

**Source Template**: `hooks/post_tool_use.py`

**Trigger**: After editing .py files

**Purpose**: Automatic code formatting with black + isort

**Implementation**:
```python
# File: .claude/hooks/auto_format_python.py

import subprocess
import json
import sys

def main():
    # Read hook payload
    payload = json.loads(sys.stdin.read())

    # Check if Python file was edited
    if payload.get('tool') == 'Edit':
        file_path = payload.get('parameters', {}).get('file_path', '')

        if file_path.endswith('.py'):
            # Run black
            subprocess.run(['black', file_path], check=False)

            # Run isort
            subprocess.run(['isort', file_path], check=False)

            print(f"Auto-formatted: {file_path}")

if __name__ == '__main__':
    main()
```

**Configuration** (.claude/settings.local.json):
```json
{
  "hooks": {
    "PostToolUse": {
      "path": ".claude/hooks/auto_format_python.py",
      "enabled": true,
      "timeout": 5000
    }
  }
}
```

**Expected Impact**: Zero manual formatting, PEP 8 compliance automatic

---

### 2.2 Import Validation (post_tool_use.py)

**Trigger**: After editing .py files

**Purpose**: Immediate feedback on import issues

**Implementation**:
```python
# File: .claude/hooks/validate_imports.py

import subprocess
import json
import sys

def main():
    payload = json.loads(sys.stdin.read())

    if payload.get('tool') == 'Edit':
        file_path = payload.get('parameters', {}).get('file_path', '')

        if file_path.endswith('.py'):
            # Run pyflakes
            result = subprocess.run(
                ['python', '-m', 'pyflakes', file_path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"Import issues detected in {file_path}:")
                print(result.stdout)

if __name__ == '__main__':
    main()
```

**Expected Impact**: Catch import errors immediately, not at runtime

---

### 2.3 Test Reminder (post_tool_use.py)

**Trigger**: After creating/editing .py files in app/

**Purpose**: Remind to create/update tests

**Implementation**:
```python
# File: .claude/hooks/test_reminder.py

import os
import json
import sys

def main():
    payload = json.loads(sys.stdin.read())

    if payload.get('tool') in ['Write', 'Edit']:
        file_path = payload.get('parameters', {}).get('file_path', '')

        # Check if production code in api/app/
        if 'api/app/' in file_path and file_path.endswith('.py'):
            # Find corresponding test file
            test_path = file_path.replace('api/app/', 'api/tests/')
            test_path = test_path.replace('.py', '_test.py')

            if not os.path.exists(test_path):
                print(f"\nREMINDER: Create test for {file_path}")
                print(f"Expected location: {test_path}")
                print(f"Run: pytest {test_path} -v")

if __name__ == '__main__':
    main()
```

**Expected Impact**: Never forget to write tests, TDD enforced

---

### 2.4 Coverage Badge Update (post_tool_use.py)

**Trigger**: After pytest runs

**Purpose**: Update coverage badge automatically

**Implementation**:
```python
# File: .claude/hooks/update_coverage_badge.py

import re
import json
import sys

def main():
    payload = json.loads(sys.stdin.read())

    if payload.get('tool') == 'Bash':
        command = payload.get('parameters', {}).get('command', '')
        output = payload.get('output', '')

        if 'pytest' in command and '--cov' in command:
            # Extract coverage percentage
            match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)

            if match:
                coverage_pct = match.group(1)
                print(f"\nCoverage: {coverage_pct}%")

                # Update README badge (if needed)
                # TODO: Implement badge update logic

if __name__ == '__main__':
    main()
```

**Expected Impact**: Always up-to-date coverage metrics

---

### 2.5 Excel Export Validation (post_tool_use.py)

**Trigger**: After modifying Excel export code

**Purpose**: Auto-run Excel tests

**Implementation**:
```python
# File: .claude/hooks/excel_test_trigger.py

import subprocess
import json
import sys

def main():
    payload = json.loads(sys.stdin.read())

    if payload.get('tool') in ['Edit', 'Write']:
        file_path = payload.get('parameters', {}).get('file_path', '')

        # Check if Excel export code modified
        if 'api/app/domain/export/excel/' in file_path:
            print("\nExcel export modified. Running tests...")

            result = subprocess.run(
                ['pytest', 'api/tests/domain/export/excel/', '-v'],
                cwd='.',
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print("Excel tests FAILED!")
                print(result.stdout)

if __name__ == '__main__':
    main()
```

**Expected Impact**: Catch Excel bugs immediately after code change

---

## Phase 2 Summary

**Total Time**: 4 hours
**Hooks Created**: 5
**Expected Impact**:
- Zero manual formatting (saves 5 min/day = 20 hours/year)
- Immediate import error feedback (saves 10 min/bug = 8 hours/year)
- TDD enforced automatically (test coverage maintained)
- Coverage always up-to-date (better visibility)
- Excel bugs caught immediately (zero production Excel bugs)

---

## Phase 3: Custom Commands (Week 3, 8 hours)

### 3.1 /benchmark - Performance Testing

**Source Template**: `commands/development/benchmark-template.md`

**Purpose**: Run performance benchmarks for critical operations

**Implementation**:
```markdown
# Benchmark Performance

Run comprehensive performance benchmarks for Customer Feedback Analyzer.

## Execution

```bash
# Sentiment analysis benchmark (1000 comments)
cd api
python scripts/benchmark/benchmark_sentiment.py

# Excel export benchmark (10,000 rows)
python scripts/benchmark/benchmark_excel_export.py

# Full pipeline benchmark (end-to-end)
python scripts/benchmark/benchmark_full_pipeline.py
```

## Metrics Tracked

1. Sentiment Analysis
   - Comments/second throughput
   - Avg latency per comment
   - Cache hit rate

2. Excel Export
   - Export time (by row count)
   - Memory usage peak
   - Sheet generation time breakdown

3. Full Pipeline
   - Total processing time
   - OpenAI API call count
   - Cost per 1000 comments

## Performance Targets

- Sentiment: >= 40 comments/second
- Excel: <= 30 seconds for 10k rows
- Pipeline: <= 2 minutes for 1000 comments
```

**Expected Impact**: Track performance regressions, optimize bottlenecks

---

### 3.2 /deploy-check - Pre-deployment Validation

**Purpose**: Comprehensive validation before deployment

**Implementation**:
```markdown
# Deployment Readiness Check

Validate Customer Feedback Analyzer is ready for deployment.

## Execution

```bash
# Run all validation checks
bash scripts/deployment/deploy_check.sh
```

## Checks Performed

1. Tests: All passing, coverage >= 70%
2. Type checking: mypy passes
3. Import validation: pyflakes clean
4. Repository organization: No violations
5. Docker build: Successful
6. Environment variables: All required vars set
7. Database migrations: Up to date (if applicable)
8. Excel export: Integration test passing
9. OpenAI API: Connection verified
10. Redis: Connection verified

## Success Criteria

ALL checks must pass before deployment.

## Failure Handling

If any check fails, deployment blocked with detailed error report.
```

**Expected Impact**: Zero broken deployments, faster rollback decisions

---

### 3.3 /compare-datasets - Dataset Comparison

**Purpose**: Compare feedback datasets (before/after analysis)

**Implementation**:
```markdown
# Compare Feedback Datasets

Compare two customer feedback datasets to identify differences.

## Execution

```bash
cd api
python scripts/analysis/compare_datasets.py \
  --dataset1 datasets/ftth/before_optimization.csv \
  --dataset2 datasets/ftth/after_optimization.csv \
  --output comparison_report.md
```

## Comparison Metrics

1. Row count difference
2. Column schema differences
3. Sentiment distribution changes
4. NPS score changes
5. Pain point category shifts
6. Churn risk distribution
7. Duplicate detection differences

## Output

Markdown report with:
- Summary statistics
- Visual charts (matplotlib)
- Detailed diff tables
- Recommendations
```

**Expected Impact**: Faster dataset analysis, better insights

---

### 3.4 /ftth-analysis - FTTH-Specific Analysis

**Purpose**: Run FTTH telecom-specific analysis

**Implementation**:
```markdown
# FTTH Telecom Feedback Analysis

Run specialized analysis for FTTH (fiber telecom) customer feedback.

## Execution

```bash
cd api
python scripts/analysis/ftth_analyzer.py \
  --input datasets/ftth/ftth_846_reviews.csv \
  --output results/ftth_analysis_$(date +%Y%m%d).xlsx
```

## FTTH-Specific Processing

1. Pain Point Classification (9 categories)
   - CONNECTIVITY, SPEED, SUPPORT, BILLING
   - INSTALLATION, EQUIPMENT, RELIABILITY, GENERIC, OTHER

2. Telecom Terminology Detection
   - Fiber optic, bandwidth, latency
   - Installation delays, technician visits
   - Contract issues, billing errors

3. Churn Risk Factors
   - Exit threats
   - Low satisfaction scores
   - Competitor mentions
   - Contract expiration proximity

4. Service Quality Metrics
   - Speed satisfaction
   - Reliability scores
   - Support response time mentions

## Output

Excel file with:
- 7 specialized view sheets
- 36-column calculated data
- FTTH-specific insights
- Churn risk analysis
```

**Expected Impact**: Domain-specific insights, faster telecom analysis

---

### 3.5 /validate-excel - Quick Excel Validation

**Purpose**: Fast Excel export validation (< 30 seconds)

**Implementation**:
```markdown
# Validate Excel Export

Quick validation of Customer Feedback Analyzer Excel exports.

## Execution

```bash
# Validate specific Excel file
cd api
python scripts/validation/validate_excel.py \
  --file path/to/export.xlsx \
  --schema v3.9.0

# Or use test suite
pytest api/tests/domain/export/excel/ -v
```

## Validation Checks

1. Sheet Count: 7 view sheets + Calculated Data
2. Column Count: 36 columns in Calculated Data
3. Tab Colors: RED/ORANGE/YELLOW/BLUE/PURPLE/GRAY
4. Conditional Formatting: Review Priority Score colored
5. Data Types: All columns correct types
6. No Errors: Zero #REF!, #VALUE!, #NAME! errors
7. Formula Validation: All formulas calculate (if any)

## Output

- PASS/FAIL status
- Detailed error report (if failed)
- Suggestions for fixes

## Integration

Can be used in:
- Pre-commit hooks
- CI/CD pipelines
- Manual validation
```

**Expected Impact**: Catch Excel bugs in <30 seconds, not 15 minutes

---

### 3.6 /optimize-costs - AI Cost Analysis

**Purpose**: Analyze and optimize OpenAI API costs

**Implementation**:
```markdown
# AI Cost Optimization Analysis

Analyze OpenAI API usage and identify cost optimization opportunities.

## Execution

```bash
cd api
python scripts/analysis/cost_optimizer.py \
  --logs logs/openai_metrics.log \
  --period last_30_days \
  --output cost_analysis_report.md
```

## Analysis

1. Token Usage
   - Avg tokens per comment
   - Total tokens last 30 days
   - Cost breakdown by operation

2. Cache Performance
   - Cache hit rate
   - Savings from caching
   - Opportunity for improvement

3. Batch Optimization
   - Current batch sizes
   - Optimal batch size recommendations
   - Potential savings

4. Model Selection
   - GPT-4o-mini vs GPT-4 usage
   - Cost per operation
   - Accuracy vs cost tradeoff

## Recommendations

- Increase cache TTL (if hit rate high)
- Adjust batch sizes
- Optimize prompts (reduce tokens)
- Evaluate local alternatives

## Target

87% cost reduction vs traditional (current benchmark)
```

**Expected Impact**: Maintain 87% cost savings, identify further optimizations

---

### 3.7 /pain-points - Pain Point Deep Dive

**Purpose**: Analyze pain point distribution and trends

**Implementation**:
```markdown
# Pain Point Analysis

Deep dive into pain point categories and trends.

## Execution

```bash
cd api
python scripts/analysis/pain_point_analyzer.py \
  --input datasets/ftth/ftth_846_reviews.csv \
  --output pain_point_report.html
```

## Analysis

1. Category Distribution
   - Primary pain points (%)
   - Secondary pain points (%)
   - Keyword frequency

2. Trends Over Time (if timestamps available)
   - Emerging pain points
   - Declining pain points
   - Seasonal patterns

3. Correlation Analysis
   - Pain points vs NPS
   - Pain points vs churn risk
   - Pain points vs sentiment

4. Actionability
   - High-impact, fixable issues
   - Low-impact, ignore
   - Medium-impact, roadmap

## Output

Interactive HTML report with:
- Charts (matplotlib/plotly)
- Detailed tables
- Keyword clouds
- Recommendations
```

**Expected Impact**: Product roadmap informed by data, prioritize fixes

---

### 3.8 /test-coverage - Coverage Deep Dive

**Purpose**: Detailed test coverage analysis

**Implementation**:
```markdown
# Test Coverage Analysis

Comprehensive test coverage analysis and improvement recommendations.

## Execution

```bash
cd api
python scripts/testing/coverage_analyzer.py \
  --threshold 70 \
  --target 85 \
  --output coverage_report.html
```

## Analysis

1. Overall Coverage
   - Current: X%
   - Target: 85%
   - Gap: Y%

2. Module Breakdown
   - Critical modules (should be 85%+)
   - Low coverage modules (<70%)
   - Missing tests entirely

3. Untested Code
   - Line numbers
   - Functions without tests
   - Branches not covered

4. Improvement Plan
   - Priority modules to test
   - Estimated time per module
   - Total time to reach 85%

## Output

- HTML report with drill-down
- TODO list for test creation
- Risk assessment
```

**Expected Impact**: Roadmap to 85% coverage, identify gaps

---

## Phase 3 Summary

**Total Time**: 8 hours
**Commands Created**: 8
**Expected Impact**:
- Performance tracking (prevent regressions)
- Deployment confidence (zero broken deployments)
- Dataset insights (faster analysis)
- Domain expertise (FTTH specialization)
- Quality gates (Excel validation <30 sec)
- Cost optimization (maintain 87% savings)
- Product roadmap (data-driven)
- Test coverage (clear path to 85%+)

---

## Implementation Roadmap

### Week 1: Core Skills (6 hours)
- Day 1-2: Excel Export Validator (1h) + Systematic Testing (1.5h)
- Day 3: Systematic Debugging (1h) + Import Quality (45 min)
- Day 4-5: Verification Before Completion (30 min) + Code Review (1h)
- Deliverables: 6 active skills, immediate quality improvements

### Week 2: Automation Hooks (4 hours)
- Day 1: Auto-format Python (1h) + Import Validation (1h)
- Day 2: Test Reminder (1h) + Coverage Badge (30 min)
- Day 3: Excel Export Validation (30 min)
- Deliverables: 5 automation hooks, zero manual quality checks

### Week 3: Custom Commands (8 hours)
- Day 1: /benchmark (2h) + /deploy-check (2h)
- Day 2: /compare-datasets (1h) + /ftth-analysis (2h)
- Day 3: /validate-excel (30 min) + /optimize-costs (1h)
- Day 4: /pain-points (1.5h) + /test-coverage (1h)
- Deliverables: 8 custom commands, complete workflow automation

### Week 4: Testing & Refinement (4 hours)
- Test all skills activation
- Refine hook triggers
- Optimize command outputs
- Documentation updates
- Team training

---

## Expected ROI

### Time Savings
- Excel validation: 4.8 hours/month
- Auto-formatting: 1.6 hours/month
- Import validation: 0.7 hours/month
- Test reminders: 2 hours/month (fewer missed tests)
- Debugging: 5 hours/month (50% reduction)
- Code review: 3 hours/month (30% faster)
- **Total: 17.1 hours/month = 205 hours/year**

### Cost Savings
- Fewer production bugs: $2000/year (reduced debugging, support)
- Maintained AI optimization: $5592/year (87% savings maintained)
- Faster deployments: $1000/year (less downtime)
- **Total: $8,592/year**

### Quality Improvements
- Test coverage: 70% -> 85%+ (60-70% fewer bugs)
- Excel bugs: Zero (100% validation)
- Import errors: Zero (100% validation)
- Code review quality: 30% improvement
- TDD adoption: 100% (enforced)

### Total Annual Value
- Time: 205 hours × $150/hour = $30,750
- Cost: $8,592
- **Total ROI: $39,342/year**

**Investment**: 22 hours (3 weeks)
**Payback Period**: 20 days
**ROI**: 1,788%

---

## Next Steps

1. Review this plan
2. Prioritize which phase to start with (recommend: Phase 1)
3. Copy first skill template to `.claude/skills/`
4. Customize description and validation rules
5. Test skill activation
6. Iterate based on usage

## Questions?

- Which phase should we start with?
- Any specific pain points to address first?
- Team training needed?
- Integration with existing tools?

---

**Created**: 2025-11-16
**Status**: Ready for implementation
**Effort**: 22 hours total
**Value**: $39K+/year
