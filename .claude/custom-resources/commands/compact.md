# Context Cleanup Command

Analyze and reduce conversation context bloat for improved performance and cost efficiency.

## Purpose

This command helps manage token usage by:
- Identifying large files in context
- Detecting repeated information
- Suggesting context cleanup strategies
- Compacting verbose outputs

## Usage

```bash
/compact
```

## What This Command Does

1. **Analyze Current Context**
   - Count tokens in conversation
   - Identify largest context contributors
   - Find repeated or redundant information

2. **Provide Cleanup Recommendations**
   - Files to close or compact
   - Sections to summarize
   - Code blocks to minimize

3. **Apply 3-File Rule**
   - Keep only 3 most relevant files open
   - Close unnecessary context
   - Suggest file rotation strategy

4. **Generate Compact Summary**
   - Summarize key points
   - Preserve critical information
   - Reduce token overhead by 60-80%

## When to Use

- Conversation feels slow or unresponsive
- Context window approaching limits
- Before starting a new complex task
- After completing a major feature
- When switching between different areas of codebase

## Example Workflow

```
User: /compact

Claude analyzes context and reports:
- Current tokens: 45,000 / 200,000 (22% usage)
- Largest contributors:
  1. CLAUDE.md (8,500 tokens)
  2. settings.local.json (6,200 tokens)
  3. Repeated git status outputs (4,800 tokens)

Recommendations:
- Close settings.local.json (already processed)
- Summarize git status to single line
- Keep CLAUDE.md (active reference)
- Estimated savings: 11,000 tokens (24% reduction)

Apply cleanup? [y/n]
```

## Implementation

Run context analysis and provide actionable cleanup plan.

## Benefits

- Faster response times
- Lower token costs
- Clearer conversation focus
- Better performance on complex tasks

## Related Commands

- `/cost` - Track API usage and costs
- `/debug` - Systematic debugging workflow
- `/refactor` - Code quality analysis
