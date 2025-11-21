# Batch API Patterns - Parallel Tool Execution

Guide to using Claude Code's batch API for parallel operations and improved performance.

## Overview

Claude Code supports **parallel tool calls** - executing multiple independent operations simultaneously for:
- 3-5x faster completion
- 40-60% cost reduction
- Better resource utilization
- Cleaner code organization

## The Pattern

### Sequential (Slow)

```
User: Read file A
Claude: [Reads A]

User: Read file B
Claude: [Reads B]

User: Read file C
Claude: [Reads C]

Total time: 6 seconds (2s per file)
API calls: 3
Cost: $0.15
```

### Parallel (Fast)

```
User: Read files A, B, and C

Claude: [Reads A, B, C simultaneously]

Total time: 2 seconds (parallel execution)
API calls: 1
Cost: $0.05

Speedup: 3x faster
Cost savings: 67%
```

## When to Use Batch API

### Perfect for Batching

1. **Reading multiple files**
   ```
   Read all test files in directory
   Read all Excel sheet modules
   Read all config files
   ```

2. **Running independent commands**
   ```
   git status + git diff + git log
   pytest + mypy + ruff
   Multiple curl requests
   ```

3. **Checking multiple conditions**
   ```
   File exists checks
   Multiple grep searches
   Parallel validations
   ```

4. **Gathering context**
   ```
   Read implementation + tests + docs
   Check multiple branches
   Query multiple APIs
   ```

### NOT for Batching

1. **Sequential dependencies**
   ```
   Bad: cd dir && ls && cat file
   (Each depends on previous)
   ```

2. **Write then read same file**
   ```
   Bad: Write file.py && Read file.py
   (Read depends on write completing)
   ```

3. **Mutations with dependencies**
   ```
   Bad: git add && git commit && git push
   (Each depends on previous success)
   ```

## Syntax

### Claude Code Batch Pattern

All operations are executed in parallel within a single tool invocation.

```markdown
User: "Check files A, B, and C for the bug"

Claude automatically batches Read operations in parallel
```

### Example: Parallel File Reads

```markdown
User: Read sentiment_scorer.py, test_sentiment_scorer.py, and analysis_thresholds.py

Claude executes all 3 reads simultaneously
Result: 3x faster than sequential
```

### Example: Parallel Git Commands

```bash
User: Show me git status, git diff, and recent commits

Claude runs:
- git status
- git diff
- git log -5

All in parallel, single response with combined results
```

## Real-World Examples

### Example 1: Code Review

```markdown
BAD (Sequential - 12 seconds):
User: Read dashboard_sheet.py
Claude: [Reads file]
User: Now read test_dashboard.py
Claude: [Reads file]
User: Now read formatters.py
Claude: [Reads file]
User: Now read colors.py
Claude: [Reads file]

GOOD (Parallel - 3 seconds):
User: Review dashboard refactoring. Read dashboard_sheet.py,
test_dashboard.py, formatters.py, and colors.py

Claude: [Reads all 4 files in parallel]

Speedup: 4x faster
Cost savings: 75%
```

### Example 2: Bug Investigation

```markdown
BAD (Sequential - 10 seconds):
User: Check if bug is in sentiment_scorer.py
Claude: [Checks file]
User: Check optimized_analyzer.py
Claude: [Checks file]
User: Check the test file
Claude: [Checks file]

GOOD (Parallel - 3 seconds):
User: Bug in sentiment analysis. Check sentiment_scorer.py,
optimized_analyzer.py, and test_sentiment_scorer.py

Claude: [Checks all 3 files simultaneously]

Speedup: 3.3x faster
```

### Example 3: Test Suite Validation

```bash
BAD (Sequential - 20 seconds):
Run pytest
(wait)
Run mypy
(wait)
Run ruff
(wait)

GOOD (Parallel - 7 seconds):
Run pytest, mypy, and ruff in parallel

All checks complete simultaneously
Speedup: 2.8x faster
```

### Example 4: Multi-File Search

```markdown
BAD (Sequential - 15 seconds):
Search for "ExcelColors" in dashboard_sheet.py
(wait)
Search in formatters.py
(wait)
Search in table_builder.py
(wait)
Search in colors.py
(wait)
Search in constants/

GOOD (Parallel - 4 seconds):
Search for "ExcelColors" across all Excel formatting modules

Claude uses parallel Grep operations
Speedup: 3.75x faster
```

## Best Practices

### 1. Be Explicit About Parallelism

```markdown
UNCLEAR:
"Read file A. Also read file B and C."

CLEAR:
"Read files A, B, and C" (implies parallel)
"Read A, B, C in parallel" (explicit)
```

### 2. Group Independent Operations

```markdown
GOOD grouping:
- All file reads together
- All git commands together
- All validations together

BAD grouping:
- Read file, then edit, then read another
  (mixed dependencies)
```

### 3. Use for Context Gathering

```markdown
Excellent use case:
"To debug this issue, I need to see:
- The implementation (sentiment_scorer.py)
- The tests (test_sentiment_scorer.py)
- The config (analysis_thresholds.py)"

Claude batches all 3 reads
```

### 4. Specify All Targets Upfront

```markdown
GOOD:
"Read all Excel sheet generators:
- dashboard_sheet.py
- full_data_sheet.py
- summary_sheet.py
- guide_sheet.py"

BAD:
"Read dashboard_sheet.py"
(later) "Also read full_data_sheet.py"
(later) "And summary_sheet.py"
```

## Performance Metrics

### Time Savings by Operation Count

```
Operations | Sequential | Parallel | Speedup | Savings
-----------|-----------|----------|---------|--------
2 files    | 4s        | 2s       | 2.0x    | 50%
3 files    | 6s        | 2s       | 3.0x    | 67%
4 files    | 8s        | 2s       | 4.0x    | 75%
5 files    | 10s       | 2.5s     | 4.0x    | 75%
10 files   | 20s       | 4s       | 5.0x    | 80%
```

### Cost Savings

```
Scenario: Reading 5 Excel module files

Sequential approach:
- 5 separate API calls
- 5 separate responses
- Total cost: $0.25

Parallel approach:
- 1 API call
- 1 response with 5 results
- Total cost: $0.08

Savings: 68% cost reduction
```

## Common Patterns for This Project

### Pattern 1: Excel Module Review

```markdown
User: Review the Excel export refactoring. Read all dashboard module files.

Claude batches:
- dashboard_sheet.py
- dashboard_builder.py
- formatters.py
- table_builder.py
- utils.py

Result: Complete module view in one shot
```

### Pattern 2: Test Coverage Check

```bash
User: Check test coverage for sentiment analysis. Run:
- pytest with coverage
- coverage report
- mypy type checking

Claude executes in parallel:
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest --cov=app/domain/feedback/sentiment_scorer
coverage report
mypy app/domain/feedback/sentiment_scorer/

Result: Complete quality report in one go
```

### Pattern 3: Multi-Dataset Analysis

```markdown
User: Analyze all telecom datasets. Read:
- FTTH_846.csv
- FTTH_1200.csv
- FTTH_sample.csv

Claude batches file reads
Result: Compare datasets simultaneously
```

### Pattern 4: Documentation Update

```markdown
User: Update documentation after refactoring. Read:
- REFACTORING_GUIDE.md
- MODULE_REFERENCE.md
- CLAUDE.md

Claude batches reads
Result: Consistent doc updates across all files
```

## Integration with Other Patterns

### Combine with 3-File Rule

```markdown
Batch read to gather context (parallel)
Keep only 3 most relevant files open (3-file rule)
Close others after processing

Best of both worlds:
- Fast context gathering (batch)
- Focused attention (3-file rule)
```

### Combine with Extended Thinking

```markdown
User: [Extended Thinking: 10K] Architecture review

Read all domain modules in parallel:
- sentiment_scorer/
- export/excel/
- upload/

Claude:
1. Batches all reads (parallel, fast)
2. Uses extended thinking for deep analysis
3. Provides comprehensive architecture feedback

Result: Fast + thorough analysis
```

### Combine with /compact

```markdown
1. Batch read for context (parallel)
2. Analyze and complete task
3. Run /compact to close files
4. Ready for next task

Efficient workflow cycle
```

## Monitoring Batch Performance

### Use /cost command

```bash
/cost

Batch API Usage:
- Parallel reads: 15 (avg 3.5 files per batch)
- Sequential reads: 5
- Batch adoption: 75%
- Time saved: 45 seconds
- Cost saved: $0.34 (23% reduction)

Recommendation: Batch more operations
Opportunity: 5 sequential reads could be batched
```

## Advanced Techniques

### 1. Nested Batching

```markdown
User: Complete code review

Claude:
- Batch 1: Read all implementation files
- Batch 2: Read all test files
- Batch 3: Run all validation tools

Result: 3 parallel batches, ultra-fast completion
```

### 2. Conditional Batching

```markdown
User: If bug exists in module A, also check modules B and C

Claude:
- Read module A
- If bug found: Batch read B and C
- Otherwise: Skip

Smart conditional parallelism
```

### 3. Tiered Batching

```markdown
Priority 1 batch: Critical files (parallel)
(wait for results)
Priority 2 batch: Supporting files (parallel)
(wait for results)
Priority 3 batch: Reference files (parallel)

Progressive context loading
```

## Common Mistakes

### Mistake 1: Not Batching Independent Operations

```markdown
BAD:
Read file 1
(wait)
Read file 2
(wait)
Read file 3

GOOD:
Read files 1, 2, and 3
```

### Mistake 2: Batching Dependent Operations

```markdown
BAD:
Write new file + Read same file in parallel
(Read fails, file doesn't exist yet)

GOOD:
Write new file
(wait)
Read new file
```

### Mistake 3: Over-Batching

```markdown
BAD:
Read 50 files in one batch
(Violates 3-file rule, context bloat)

GOOD:
Read 3-5 most relevant files
Close after processing
Batch next group if needed
```

## Quick Reference

```
Operation Type          | Batch? | Example
------------------------|--------|----------------------------
Multiple file reads     | YES    | Read A.py, B.py, C.py
Independent validations | YES    | pytest + mypy + ruff
Git info gathering      | YES    | status + diff + log
Code + tests + docs     | YES    | All independent reads
Sequential mutations    | NO     | add -> commit -> push
Write then read same    | NO     | Write file -> Read file
Dependent commands      | NO     | cd dir -> ls
```

## Expected Benefits

Implementation of batch API patterns:

- 3-5x faster operations
- 40-60% cost reduction
- Cleaner conversation flow
- Better resource utilization
- Improved developer experience

## Related Documentation

- [THREE_FILE_RULE.md](THREE_FILE_RULE.md) - Context management
- [/compact](commands/compact.md) - Context cleanup
- [/cost](commands/cost.md) - Performance tracking
- [EXTENDED_THINKING.md](EXTENDED_THINKING.md) - Complex analysis

## Summary

Batch API patterns enable parallel tool execution:

1. Group independent operations
2. Execute in parallel automatically
3. Get results in single response
4. Save time and cost
5. Maintain context efficiency

**Remember: If operations are independent, batch them. If they depend on each other, sequence them.**

---

Last Updated: 2025-11-16
Based on: Claude Code official documentation and community best practices
