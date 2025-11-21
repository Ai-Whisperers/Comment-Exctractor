---
description: Run comprehensive debugging workflow with checks
model: sonnet
---

# Debugging Workflow

Execute systematic debugging checks to identify and resolve issues.

## Debugging Steps:

1. **Syntax Check** - Verify Python syntax
2. **Import Check** - Test all imports
3. **Type Check** - Run mypy for type errors
4. **Unit Tests** - Execute test suite
5. **Integration Tests** - Check component integration
6. **Log Review** - Check recent error logs

## Execution:

!PYTHONPATH=".:$PYTHONPATH" timeout 120 ./venv/Scripts/python -m pytest -v --tb=short

## Common Issues to Check:

- `ModuleNotFoundError` - PYTHONPATH issues
- `ConnectionRefusedError` - Redis not running
- `ImportError` - Missing dependencies
- `AttributeError` - API changes
- `TypeError` - Type mismatches

## Quick Fixes:

**PYTHONPATH Issues:**

```bash
export PYTHONPATH=".:$PYTHONPATH"
```

**Redis Issues:**

```bash
docker-compose up -d redis
```

**Dependency Issues:**

```bash
pip install -r requirements.txt
```

## Log Locations:

- API logs: `api/logs/`
- Test logs: `api/tests/results/`
- Celery logs: Check docker-compose logs

Use this when encountering unexpected errors or test failures.
