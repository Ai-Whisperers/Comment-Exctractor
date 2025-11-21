# Performance Profiler Skill

Analyze and optimize performance bottlenecks in Python/TypeScript code with profiling tools and recommendations.

## Metadata

- Name: Performance Profiler
- Category: Performance & Optimization
- Activation: Automatic when performance issues mentioned
- Model: Sonnet (complex analysis)
- Token Cost: ~1,000 tokens

## When to Activate

Trigger this skill when user mentions:
- "Profile performance"
- "Optimize speed"
- "Slow function"
- "Performance bottleneck"
- "Memory leak"
- "N+1 query"
- "Caching opportunity"

## Core Capabilities

### 1. Identify N+1 Queries

Detect and fix:
- Database queries in loops
- Lazy loading performance issues
- Missing eager loading
- Inefficient ORM usage

### 2. Memory Leak Detection

Find:
- Unclosed file handles
- Circular references
- Growing caches without limits
- Event listener leaks (TypeScript)

### 3. Slow Function Analysis

Profile:
- Function execution time
- Call frequency
- Memory usage
- I/O wait time

### 4. Caching Opportunities

Suggest:
- Redis caching for expensive operations
- LRU caches for frequently-called functions
- Memoization for pure functions
- HTTP caching headers

### 5. Batch Operation Recommendations

Identify:
- Serial operations that could be parallel
- Loops that could use bulk operations
- API calls that could be batched

## Project-Specific Context

### Performance Targets

```
Excel Generation: <30 seconds for 1,000 rows
API Response Time: <200ms p95
Database Queries: <50ms p95
Memory Usage: <512MB per worker
OpenAI API Calls: <2 seconds p95
```

### Current Optimizations

1. Comment-level caching (Redis)
   - SHA256 hash for deduplication
   - 7-day TTL
   - 15-20% cost savings

2. Batch processing
   - 50-120 comments per OpenAI request
   - Dynamic batch sizing based on memory

3. OptimizedSpanishAnalyzer
   - LRU cache for sentiment results
   - Frequency-tiered lexicons
   - 20-40% faster than standard analyzer

4. Async processing
   - Celery workers for background tasks
   - Non-blocking I/O with asyncio

## Usage Examples

### Example 1: Profile Excel Export

```
User: Profile the Excel export performance

Skill analyzes:

1. Add Profiling (api/scripts/profiling/profile_excel_export.py):

import cProfile
import pstats
from app.domain.export.excel.service import ExcelExportService

def profile_export():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run export
    service = ExcelExportService()
    service.generate_export(df, schema)

    profiler.disable()

    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 slowest functions

if __name__ == "__main__":
    profile_export()

2. Run Profiling:

python api/scripts/profiling/profile_excel_export.py

Results:
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.050    0.050   28.450   28.450 service.py:45(generate_export)
       23    5.200    0.226   15.300    0.665 dashboard_builder.py:78(create_dashboard)
      846    8.100    0.010   10.200    0.012 formatters.py:112(apply_conditional_formatting)
      ...

3. Bottlenecks Identified:

- Dashboard creation: 5.2s (18% of total)
- Conditional formatting: 8.1s (29% of total)
- Sheet generation: 846 calls, 10.2s total

4. Optimization Recommendations:

a) Batch conditional formatting:

# Before (slow - 846 individual calls)
for row in range(2, len(df) + 2):
    apply_conditional_formatting(ws, row)

# After (fast - 1 bulk operation)
apply_conditional_formatting_bulk(ws, start_row=2, end_row=len(df) + 2)

b) Cache dashboard calculations:

from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_dashboard_kpis(df_hash):
    # Expensive calculations
    return {
        'nps_score': ...,
        'churn_risk_avg': ...,
        'sentiment_distribution': ...
    }

# Use hash to enable caching
df_hash = hash(tuple(df['comment'].values))
kpis = calculate_dashboard_kpis(df_hash)

Expected improvement: 40-50% faster (28s -> 15s)
```

### Example 2: N+1 Query Detection

```
User: Check for N+1 queries in the feedback analysis

Skill identifies:

1. Problem Code (api/app/application/pipeline/processor.py):

# N+1 Query Problem
feedback_items = session.query(FeedbackAnalysis).all()

for feedback in feedback_items:
    pain_points = feedback.pain_points  # Lazy load - separate query!
    for point in pain_points:
        process_pain_point(point)

# Generates: 1 + N queries (1 for feedback, N for pain_points)

2. Detection Method:

# Add query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Run code
# Output shows:
# SELECT * FROM feedback_analysis
# SELECT * FROM pain_points WHERE feedback_id = 1
# SELECT * FROM pain_points WHERE feedback_id = 2
# ... (N queries!)

3. Optimized Code:

from sqlalchemy.orm import joinedload

# Eager load relationships
feedback_items = session.query(FeedbackAnalysis)\
    .options(joinedload(FeedbackAnalysis.pain_points))\
    .all()

for feedback in feedback_items:
    pain_points = feedback.pain_points  # Already loaded!
    for point in pain_points:
        process_pain_point(point)

# Generates: 1 query (with JOIN)
# SELECT * FROM feedback_analysis
# LEFT JOIN pain_points ON feedback_analysis.id = pain_points.feedback_id

Performance improvement: 90% faster for 1,000 rows
```

### Example 3: Memory Leak Detection

```
User: Find memory leaks in the sentiment analyzer

Skill checks:

1. Memory Profiling (api/scripts/profiling/profile_memory.py):

import tracemalloc
from app.domain.feedback.sentiment_scorer import SentimentScorer

tracemalloc.start()

scorer = SentimentScorer()

# Process 1,000 comments
for i in range(1000):
    scorer.score_comment(f"Comment {i}")

    if i % 100 == 0:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        print(f"Iteration {i}:")
        for stat in top_stats[:3]:
            print(stat)

2. Results Show Growing Memory:

Iteration 0:
  sentiment_scorer.py:45: 2.5 MB

Iteration 100:
  sentiment_scorer.py:45: 5.2 MB  # Growing!

Iteration 200:
  sentiment_scorer.py:45: 7.8 MB  # Still growing!

3. Root Cause:

class SentimentScorer:
    def __init__(self):
        self.cache = {}  # Unbounded cache!

    def score_comment(self, comment):
        if comment in self.cache:
            return self.cache[comment]

        score = self._analyze(comment)
        self.cache[comment] = score  # Memory leak!
        return score

4. Fix with LRU Cache:

from functools import lru_cache

class SentimentScorer:
    @lru_cache(maxsize=1000)  # Limit to 1,000 entries
    def score_comment(self, comment):
        return self._analyze(comment)

# Or use Redis with TTL
def score_comment(self, comment):
    cached = redis_client.get(f"sentiment:{hash(comment)}")
    if cached:
        return json.loads(cached)

    score = self._analyze(comment)
    redis_client.setex(
        f"sentiment:{hash(comment)}",
        86400,  # 24 hour TTL
        json.dumps(score)
    )
    return score

Memory usage after fix: Stable at 3.5 MB
```

## Best Practices Enforced

### 1. Profile Before Optimizing

```python
# Always measure first
import timeit

# Time a function
execution_time = timeit.timeit(
    "slow_function(data)",
    setup="from module import slow_function, data",
    number=100
)

print(f"Average time: {execution_time / 100:.4f} seconds")
```

### 2. Use Async for I/O-Bound Operations

```python
# Before (blocking)
def process_comments(comments):
    results = []
    for comment in comments:
        result = openai_client.complete(comment)  # Blocks!
        results.append(result)
    return results

# After (non-blocking)
async def process_comments(comments):
    tasks = [openai_client.complete_async(c) for c in comments]
    results = await asyncio.gather(*tasks)
    return results

# 10x faster for I/O-bound operations
```

### 3. Batch Database Operations

```python
# Before (slow - N queries)
for row in data:
    session.add(FeedbackAnalysis(**row))
    session.commit()

# After (fast - 1 query)
session.bulk_insert_mappings(FeedbackAnalysis, data)
session.commit()

# 100x faster for bulk inserts
```

### 4. Use Generators for Large Datasets

```python
# Before (loads entire dataset into memory)
def process_large_file(path):
    df = pd.read_csv(path)  # 500 MB file!
    return [process_row(row) for row in df.itertuples()]

# After (streams data, low memory)
def process_large_file(path):
    for chunk in pd.read_csv(path, chunksize=1000):
        for row in chunk.itertuples():
            yield process_row(row)

# Memory usage: 500 MB -> 5 MB
```

### 5. Cache Expensive Computations

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=128)
def calculate_sentiment_score(comment_hash):
    # Expensive NLP processing
    return score

# Hash comments to enable caching
def score_comment(comment):
    comment_hash = hashlib.sha256(comment.encode()).hexdigest()
    return calculate_sentiment_score(comment_hash)
```

## Profiling Tools

### Python Profiling

```python
# 1. cProfile (built-in, comprehensive)
import cProfile
cProfile.run('slow_function()')

# 2. line_profiler (line-by-line timing)
from line_profiler import LineProfiler

profiler = LineProfiler()
profiler.add_function(slow_function)
profiler.run('slow_function()')
profiler.print_stats()

# 3. memory_profiler (memory usage)
from memory_profiler import profile

@profile
def memory_intensive_function():
    ...

# 4. py-spy (live profiling, no code changes)
py-spy record -o profile.svg -- python script.py
```

### Database Profiling

```python
# SQLAlchemy query timing
import time
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.05:  # Log slow queries
        print(f"SLOW QUERY ({total:.2f}s): {statement}")
```

### TypeScript/React Profiling

```typescript
// React DevTools Profiler
import { Profiler } from 'react';

<Profiler id="AnalyzerPage" onRender={onRenderCallback}>
  <AnalyzerPage />
</Profiler>

function onRenderCallback(
  id, phase, actualDuration, baseDuration, startTime, commitTime
) {
  console.log(`${id} took ${actualDuration}ms`);
}

// Chrome DevTools Performance
// 1. Open DevTools (F12)
// 2. Performance tab
// 3. Record
// 4. Stop recording
// 5. Analyze flame graph
```

## Performance Metrics

### Target Benchmarks

```python
# Excel Generation
- 1,000 rows: <30 seconds
- 10,000 rows: <5 minutes
- Memory: <512 MB

# API Endpoints
- /upload: <200ms (excluding file upload)
- /status: <50ms
- /analyze: <2 seconds for 100 comments

# Database Queries
- Simple SELECT: <10ms
- Complex JOIN: <50ms
- Bulk INSERT: <100ms for 1,000 rows

# OpenAI API
- Single request: <2 seconds
- Batch (120 comments): <30 seconds
```

### Monitoring Setup

```python
# Add metrics to code
from app.infrastructure.observability.metrics import track_performance

@track_performance("excel_export")
def generate_export(df, schema):
    # Track automatically:
    # - Execution time
    # - Memory usage
    # - Error rate
    ...

# View metrics
python scripts/monitoring/view_metrics.py --last-hour
```

## Quick Reference

```bash
# Profile Python script
python -m cProfile -s cumulative script.py

# Memory profiling
python -m memory_profiler script.py

# Live profiling (no code changes)
py-spy record -o profile.svg -- python script.py

# Database query analysis
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
# Run your code
"

# React profiling
# Open Chrome DevTools -> Performance -> Record

# Benchmark comparison
python -m timeit -n 100 "slow_function()"
python -m timeit -n 100 "fast_function()"
```

## Success Criteria

Performance optimization is complete when:

- [ ] Profiling data collected and analyzed
- [ ] Bottlenecks identified (top 3-5)
- [ ] N+1 queries eliminated
- [ ] Memory leaks fixed
- [ ] Caching implemented for expensive operations
- [ ] Batch operations used where possible
- [ ] Performance targets met
- [ ] Benchmarks documented
- [ ] Monitoring in place

## Related Files

- [api/scripts/profiling/](../../../api/scripts/profiling/) - Profiling scripts
- [api/app/infrastructure/observability/](../../../api/app/infrastructure/observability/) - Metrics
- [CLAUDE.md](../../../CLAUDE.md) - Performance optimization notes

## Version

Last Updated: 2025-11-16
Status: Ready for use
