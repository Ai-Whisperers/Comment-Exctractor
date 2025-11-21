---
description: Run the full test suite with proper PYTHONPATH configuration
---

# Run Full Test Suite

!PYTHONPATH=".:$PYTHONPATH" timeout 120 ./venv/Scripts/python -m pytest -v --tb=short
