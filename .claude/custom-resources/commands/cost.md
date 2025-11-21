# Cost Tracking Command

Monitor and analyze Claude Code API usage and costs for budget optimization.

## Purpose

Track API usage patterns to:
- Monitor daily/weekly/monthly costs
- Identify expensive operations
- Optimize model selection (Sonnet vs Haiku)
- Prevent budget overruns
- Generate cost reports

## Usage

```bash
/cost [period]
```

Options:
- `/cost` - Today's usage
- `/cost week` - Last 7 days
- `/cost month` - Last 30 days
- `/cost report` - Detailed breakdown

## What This Command Does

1. **Current Session Costs**
   - Input tokens used
   - Output tokens generated
   - Model distribution (Sonnet/Haiku/Opus)
   - Estimated cost

2. **Historical Analysis**
   - Daily cost trends
   - Most expensive operations
   - Cost per feature/task
   - Optimization opportunities

3. **Budget Alerts**
   - Daily limit tracking
   - Monthly budget status
   - Cost anomaly detection
   - Projection to end of month

4. **Optimization Recommendations**
   - Operations to optimize
   - Model routing suggestions
   - Context reduction opportunities
   - Batch operation benefits

## Expected Output

```
=== Claude Code Cost Report ===

Current Session:
- Input tokens: 12,450
- Output tokens: 3,200
- Model: claude-sonnet-4-5
- Estimated cost: $0.18

Today (Nov 16, 2025):
- Total cost: $2.34
- Sessions: 3
- Avg cost/session: $0.78
- Primary operations: Testing (45%), Refactoring (30%), Docs (25%)

This Week:
- Total cost: $14.67
- Daily average: $2.10
- Trending: +15% vs last week
- Projection (month): $63.00

Top Cost Drivers:
1. Excel generation tests - $4.23 (28.8%)
2. Code refactoring - $3.56 (24.3%)
3. Documentation review - $2.89 (19.7%)

Optimization Opportunities:
- Use Haiku for test runs: Save $1.20/day (57% reduction)
- Batch Excel tests: Save $0.80/day (18% reduction)
- Enable local caching: Save $0.60/day (12% reduction)

Estimated monthly savings: $78/month (42% reduction)

Budget Status:
- Monthly budget: $100
- Current spend: $14.67 (14.7%)
- Projected: $63.00 (63%)
- Remaining buffer: $37 (37%)
```

## Cost Optimization Tips

1. **Model Selection**
   - Sonnet: Complex reasoning, planning, review
   - Haiku: Fast execution, tests, simple edits (90% cheaper)
   - Opus: Only for critical/complex tasks

2. **Context Management**
   - Use /compact regularly
   - Apply 3-file rule
   - Close large files after processing
   - Summarize long outputs

3. **Batch Operations**
   - Group related tasks
   - Run tests once at end
   - Combine file reads
   - Use parallel tool calls

4. **Caching Strategy**
   - Enable prompt caching
   - Reuse common contexts
   - Structure for cache hits
   - Monitor cache effectiveness

## Integration with Project

This command analyzes:
- OpenAI API costs (feedback analysis)
- Claude Code costs (development)
- Combined cost metrics
- ROI calculations

## When to Use

- End of each session
- Before starting expensive operations
- Weekly cost reviews
- Monthly budget planning
- After implementing optimizations

## Configuration

Add to `.env.local`:
```bash
# Cost tracking
CLAUDE_DAILY_BUDGET=5.00
CLAUDE_MONTHLY_BUDGET=100.00
ENABLE_COST_ALERTS=true
COST_ALERT_THRESHOLD=80  # Percentage

# Model preferences
PREFERRED_MODEL_SIMPLE=haiku
PREFERRED_MODEL_COMPLEX=sonnet
```

## Benefits

- **Visibility**: Know exactly what you're spending
- **Control**: Stay within budget limits
- **Optimization**: Identify and fix cost drivers
- **ROI**: Measure value vs cost

## Expected Savings

Based on community research:
- Model routing: 71% cost reduction
- Context optimization: 60-80% token savings
- Batch operations: 40-50% fewer API calls
- Caching: 30-40% cost reduction

Combined potential: 85% cost reduction

## Related Commands

- `/compact` - Reduce context bloat
- `/analyze-usage` - Usage pattern analysis
- `/benchmark` - Performance testing
