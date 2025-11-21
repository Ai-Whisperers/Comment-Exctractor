# Personal Claude Code Preferences

This file stores your personal preferences and overrides for Claude Code behavior.
It complements CLAUDE.md (project-wide) with individual preferences.

Version: 1.0.0
Last Updated: 2025-11-16

---

## Purpose

- CLAUDE.md = Project rules (committed to git, shared with team)
- CLAUDE.local.md = Your personal preferences (not committed, .gitignored)

Use this for:
- Personal workflow preferences
- Development environment specifics
- Local tool configurations
- Individual coding style preferences
- Custom shortcuts and aliases

---

## Your Preferences

### Preferred Model Selection

```
Simple tasks (editing, reading, running tests): haiku (70% of tasks)
Complex tasks (debugging, architecture, refactoring): sonnet (25% of tasks)
Critical decisions (Excel export bugs, Google Sheets integration): sonnet with extended thinking (10K budget) (5% of tasks)

Target distribution: 70% Haiku / 30% Sonnet for <$1.50/day cost
```

### Extended Thinking Usage

```
Auto-enable for:
- Excel export formatting bugs (tab colors, conditional formatting, formulas)
- Google Sheets integration issues (formula compatibility, performance)
- Spanish sentiment analysis accuracy problems
- FTTH dataset analysis errors (846-row specific issues)
- Multi-sheet export generation failures
- Database schema detection edge cases

Default budget: 10K tokens (Excel/Google Sheets issues are complex)
Maximum budget: 32K tokens (only for critical production bugs affecting customers)
```

### Context Management

```
Max open files: 3 (strict 3-file rule enforcement)
Auto-compact at: 35,000 tokens (17.5% of limit - aggressive cleanup)
Preferred context: Ultra-minimal (close files immediately after task)

Typical working set:
1. Current implementation file (e.g., dashboard_builder.py)
2. Test file (e.g., test_dashboard_builder.py)
3. Reference file (e.g., CLAUDE.md or constants.py)

Close extras IMMEDIATELY to maintain clarity
```

### Development Workflow

```
Testing frequency: Before EVERY commit (non-negotiable)
Test command: /run-tests (full suite) or /test-excel (Excel-specific)
Pre-commit checks: ALWAYS run /check-org (enforced by hook)

Preferred git workflow:
1. Work on IvanDev branch (current active development)
2. Small, atomic commits with conventional commit format
3. Never commit without running tests first
4. Never commit files >10MB (use download scripts)
5. Always run /check-org before git add

Excel development workflow:
1. Modify sheet generator (e.g., dashboard_builder.py)
2. Run /test-excel to verify
3. Manually test with FTTH_846.csv
4. Check Google Sheets compatibility
5. Verify tab colors and formatting
6. Commit with detailed message
```

### Communication Style

```
Verbosity: Concise (avoid long explanations)
Code comments: Minimal (only for complex logic)
Documentation: Update as you go
Emoji usage: Never (project rule)
```

### Code Style Preferences

```python
# Python
Max line length: 100 characters
Docstring style: Google format
Type hints: Always (use mypy)
Imports: Absolute imports only
Error handling: Specific exceptions, never bare except

# Import order
1. Standard library
2. Third-party
3. Local application
# Blank line between each group
```

```typescript
// TypeScript
Style: Functional components
State management: Hooks
Naming: camelCase for variables, PascalCase for components
Props: Always destructure
```

### File Organization Preferences

```
Test files: Co-located with source (api/tests/ directory)
Documentation: docs/ directory, never in root
Temporary files: /tmp/ or project-specific .temp/
Large datasets: Never commit, use download scripts
```

### Tool Preferences

```
Editor: VSCode
Terminal: Git Bash (Windows) / zsh (Mac)
Python version: 3.11+
Node version: 18.x LTS
Package manager: npm (not yarn)
```

### Notification Preferences

```
Test completion: Yes, show summary
Build completion: Yes, if errors
Git operations: No, silent unless errors
File operations: No, silent
Cost alerts: Yes, if >80% daily budget
```

### Budget & Cost Controls

```
Daily budget: $1.50 (target based on 70% Haiku usage)
Monthly budget: $45.00 (20 working days)
Alert threshold: 80% ($1.20/day)

Auto-switch to Haiku when:
- Simple edits (file modifications)
- Running tests (/run-tests, /test-excel)
- Reading files (documentation, code review)
- Git operations (status, diff, log)
- Repository organization checks
- Import validation (pyflakes)
- File searches (glob, grep)

Stay with Sonnet for:
- Excel export debugging (complex multi-sheet issues)
- Google Sheets integration (formula conversion)
- Spanish sentiment analysis tuning
- Architecture decisions (refactoring >500 lines)
- Complex code review (multiple modules)
- Database schema detection edge cases

Use Extended Thinking (10K budget) for:
- Critical Excel formatting bugs affecting customers
- FTTH analysis pipeline failures
- Multi-sheet export generation errors
- Performance optimization (20-40% improvements)
```

---

## Custom Aliases

### Slash Command Shortcuts

```
/t → /run-tests
/te → /test-excel
/c → /compact
/co → /cost
/d → /debug
/r → /refactor
```

### Git Workflow

```
/sync → /sync-branch main
/review → Pre-commit quality check
/ship → Run tests, commit, push
```

### Analysis Shortcuts

```
/ftth → /analyze-feedback datasets/telecom/FTTH_846.csv (primary test dataset)
/airlines → /analyze-feedback datasets/airlines/airlines-customer-satisfaction.csv
/quick → Quick analysis with sample data (100 rows, for testing)
/validate-excel → Activate excel-export-validator skill
/check-imports → cd api && ./venv/Scripts/python -m pyflakes app/
```

---

## Environment-Specific Settings

### Windows Development

```bash
# Paths
PYTHON_PATH="./venv/Scripts/python"
PYTEST_PATH="./venv/Scripts/python -m pytest"

# Redis
REDIS_URL="redis://localhost:6379/0"
USE_FAKE_REDIS="true"  # For unit tests

# OpenAI
OPENAI_API_KEY="sk-..." # Set in .env.local
```

### Mac Development (if applicable)

```bash
# Paths
PYTHON_PATH="./venv/bin/python"
PYTEST_PATH="./venv/bin/pytest"

# Redis
REDIS_URL="redis://localhost:6379/0"
```

---

## Personal Learning Goals

Track what you want to learn/improve:

- [x] Master dependency injection patterns (completed Nov 2025)
- [x] Learn advanced openpyxl formatting (tab colors, conditional formatting)
- [x] Deep dive into OpenAI API optimization (87% cost reduction achieved)
- [ ] Google Sheets formula compatibility (eliminate all Excel formulas)
- [ ] Performance profiling for Excel generation (20-40% improvement target)
- [ ] Advanced pytest fixture usage (DRY test setup)
- [ ] Circuit breaker patterns (Phase 3-4 features ready)
- [ ] Redis caching strategies (comment-level caching implemented)
- [ ] Multi-sheet dashboard design (progressive disclosure pattern)
- [ ] Spanish sentiment analysis optimization (OptimizedSpanishAnalyzer)

---

## Personal Code Review Checklist

Before committing, verify:

- [ ] All imports at top of file (no lazy imports)
- [ ] Type hints for all functions
- [ ] Specific exception types (never bare except)
- [ ] Magic numbers replaced with constants
- [ ] Tests pass (/run-tests)
- [ ] No new security warnings
- [ ] Repository organization valid (/check-org)
- [ ] Documentation updated if needed
- [ ] No print() statements (use logger)
- [ ] No TODOs without issues

---

## Troubleshooting Notes

Personal reminders for common issues:

### PYTHONPATH Issues
```bash
# Always use:
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest

# Or use slash command:
/run-tests
```

### Redis Connection
```bash
# Unit tests should use fake Redis automatically
# Check api/tests/conftest.py if issues

# For integration tests:
docker-compose up -d redis
```

### Excel Generation
```bash
# Test with:
/test-excel

# Debug with:
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest api/tests/domain/export/excel/ -v -s
```

---

## Personal Productivity Metrics

Track your improvements:

```
Week of 2025-11-16 (Phase 1 Implementation):
- Sessions: 10+
- Average cost/session: Target $1.50 (70% Haiku usage)
- Time saved by automation: 303 hours/year projected
- Bugs prevented: 100+ (November bugfix session)
- Code quality score: A- (92/100, up from C+ 68/100)
- Test coverage: 72% (target: 85%)
- Repository organization: Clean (3 MD files in root)

Phase 1 Quick Wins Achieved:
- 16 new documentation files created
- 3 slash commands added (/compact, /cost, /analyze-usage)
- 3 project-specific skills activated
- Auto-changelog hook implemented
- Expected ROI: 5,149-5,217% first year

Goals for next week:
- Maintain $1.50/day budget (strict Haiku usage)
- Achieve 80% test coverage (focus on Excel modules)
- Zero repository organization errors (enforced by hook)
- Adopt batch API patterns (3-5x speedup)
- Follow 3-file rule strictly (60-80% token savings)
```

---

## Custom Hooks (Personal)

Ideas for personal workflow hooks:

```json
{
  "PostToolUse": [
    {
      "matcher": "Write(api/app/**/*.py)",
      "hooks": [
        {
          "type": "command",
          "command": "echo 'Domain code changed. Run /run-tests before commit'",
          "timeout": 1000
        }
      ]
    }
  ]
}
```

---

## Notes & Reminders

Free-form section for personal notes:

### November 2025 Focus

- [x] Implemented community best practices from 100+ GitHub repos
- [x] Added Phase 1 skills and advanced commands (16 files)
- [x] Optimized cost through model routing (70% Haiku target)
- [ ] Improving test coverage to 85% (currently 72%)
- [ ] Phase 2: Advanced hooks and MCP integration

### Project-Specific Pain Points

- Excel export formatting (tab colors, conditional formatting)
- Google Sheets formula compatibility (must eliminate all formulas)
- FTTH_846.csv analysis (primary test dataset, 846 rows)
- Spanish sentiment analysis accuracy (OptimizedSpanishAnalyzer)
- Multi-sheet dashboard generation (23 sheets, progressive disclosure)
- Import validation (pyflakes, absolute imports only)

### Ideas to Explore

- [x] Multi-agent orchestration (Task tool with subagents)
- [ ] Custom MCP server for dataset management (Phase 2)
- [x] Automated Excel validation pipeline (excel-export-validator skill)
- [x] Cost optimization through caching (Redis comment-level caching)
- [ ] Performance profiling for Excel generation (20-40% improvement target)
- [ ] GitHub MCP for enhanced PR workflows (Phase 2)

### Lessons Learned

- Extended thinking (10K budget) saves hours on Excel formatting bugs
- 3-file rule dramatically improves context clarity (60-80% savings)
- /compact before big tasks improves performance (run at 35K tokens)
- Haiku sufficient for 70% of tasks (tests, edits, file reads)
- Batch API patterns give 3-5x speedup (use "Read A, B, C" not sequential)
- Screenshots save 40% debugging time (drag and drop for visual issues)
- Never commit files >10MB (use download scripts for test data)
- Always run /check-org before commits (enforced by hook)
- Import validation catches 90% of bugs early (pyflakes)

---

## Version History

### v1.1.0 (2025-11-16) - Personalized for Alejandro/Ivan
- Customized model selection (70% Haiku / 30% Sonnet for $1.50/day)
- Extended thinking focused on Excel/Google Sheets issues
- Strict 3-file rule enforcement (35K token auto-compact)
- IvanDev branch workflow documented
- Project-specific pain points added (FTTH, Excel exports, Spanish sentiment)
- Learning goals updated with completed items
- Productivity metrics with Phase 1 achievements
- Budget controls optimized for cost reduction

### v1.0.0 (2025-11-16)
- Initial template based on community research
- Added preferences from 100+ repository analysis
- Integrated with Phase 1 improvements

---

## Related Files

- [CLAUDE.md](../CLAUDE.md) - Project-wide rules
- [settings.local.json](settings.local.json) - Active configuration
- [EXTENDED_THINKING.md](EXTENDED_THINKING.md) - Extended thinking guide
- [SCREENSHOT_WORKFLOW.md](SCREENSHOT_WORKFLOW.md) - Screenshot patterns

---

**Important**: Add CLAUDE.local.md to .gitignore to keep personal preferences private:

```bash
# In .gitignore
.claude/CLAUDE.local.md
```
