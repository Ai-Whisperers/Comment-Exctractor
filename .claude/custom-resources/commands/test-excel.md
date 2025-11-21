---
description: Run Excel service tests with proper PYTHONPATH
---

# Test Excel Service

!PYTHONPATH=".:./scripts/excel" timeout 120 ./venv/Scripts/python -m pytest api/tests/services/excel/ -v --tb=short
