# Claude Code Custom Resources

Professional skills, hooks, commands, and agents for Claude Code - organized and ready to use.

## Overview

**Status**: Cleaned and organized (November 16, 2025)
**Total Resources**: 247 templates
**Source**: 14 curated repositories organized by function
**Size**: 2.8MB (reduced from 5.5MB via deduplication)

## Directory Structure

```
.claude/custom-resources/
├── organized/              # Library of 247 professional templates
│   ├── agents/            # 49 specialized agents
│   ├── commands/          # 63 slash command templates
│   ├── guides/            # 5 meta-guides
│   ├── hooks/             # 8 lifecycle hooks (Python)
│   ├── skills/            # 122 skills across 20 categories
│   └── templates/         # Reusable patterns
│
├── INDEX.md               # Complete resource inventory (729 lines)
├── QUICK_START.md         # Usage guide and examples (270 lines)
├── IMPROVEMENT_PLAN.md    # Project-specific customization roadmap (1,512 lines)
└── README.md              # This file

```

## Resource Categories

### Skills (122 total)
Organized by function across 20 categories:

- **Testing** (9): TDD patterns, coverage, E2E testing
- **Code Quality** (20): Code review, verification, best practices
- **Excel** (1): Excel/XLSX processing and generation
- **Data Analysis** (3): Feedback processing, data analysis
- **Debugging** (2): Systematic debugging, root cause analysis
- **Git** (4): Git workflows, branching, PR management
- **Deployment** (10): CI/CD, migrations, Docker
- **Security** (1): Security scanning, SAST
- **Development** (14): Python, JavaScript, API patterns
- **Infrastructure** (13): Cloud, Kubernetes, observability
- **Database** (2): PostgreSQL, SQL optimization
- **LLM Development** (4): LangChain, RAG, prompt engineering
- And 8 more categories...

### Hooks (8 Python hooks)
Lifecycle automation for all Claude Code events:

- `user_prompt_submit.py` - Before user input
- `pre_tool_use.py` - Before tool execution
- `post_tool_use.py` - After tool completes
- `stop.py` - When agent stops
- `subagent_stop.py` - When subagent finishes
- `pre_compact.py` - Before context compaction
- `session_start.py` - Session initialization
- `notification.py` - System notifications

### Commands (63 templates)
Slash command templates by category:

- Testing, Git, Deployment, Code Quality, Security
- Excel, Data Analysis, Debugging, Documentation
- Architecture, Refactoring, and more

### Agents (49 templates)
Specialized agents by domain:

- **Engineering** (20): Backend, Frontend, DevOps, ML, Security, QA
- **Compliance** (14): FDA, GDPR, ISO13485, MDR, CAPA, Risk Management
- **Product** (6): Product Manager, Agile PO, UX Designer
- **C-Level** (2): CEO Advisor, CTO Advisor
- **Marketing** (3): Content Creator, Demand Gen, Product Marketing
- **Other** (4): Code Quality, Data Analysis, Excel, Testing specialists

## Quick Start

### 1. Browse Available Resources

```bash
# View complete inventory
cat .claude/custom-resources/INDEX.md

# See usage examples
cat .claude/custom-resources/QUICK_START.md

# Review project-specific customization plan
cat .claude/custom-resources/IMPROVEMENT_PLAN.md
```

### 2. Install a Skill

```bash
# Copy template to active skills directory
cp .claude/custom-resources/organized/skills/testing/tdd-superpowers.md \
   .claude/skills/tdd/SKILL.md

# Customize for your project
```

### 3. Install a Hook

```bash
# Copy Python hook to active hooks directory
cp .claude/custom-resources/organized/hooks/post_tool_use.py \
   .claude/hooks/my_hook.py

# Customize logic as needed
```

### 4. Create a Command

```bash
# Copy command template
cp .claude/custom-resources/organized/commands/testing/run-tests.md \
   .claude/commands/my-test.md

# Customize and use with /my-test
```

## Project-Specific Customizations

The `IMPROVEMENT_PLAN.md` provides a 3-phase roadmap for customizing these templates for the Customer Feedback Analyzer project:

- **Phase 1 (Week 1)**: 6 core quality and testing skills
- **Phase 2 (Week 2)**: 5 automation hooks for workflow efficiency
- **Phase 3 (Week 3)**: 8 custom commands for project-specific workflows

Expected impact:
- 50+ hours/year time savings
- 70% to 85%+ test coverage improvement
- Zero Excel export bugs
- Automated code quality enforcement

## Documentation

### Primary Files

- **INDEX.md** (729 lines) - Complete resource inventory with descriptions
- **QUICK_START.md** (270 lines) - Usage guide with examples
- **IMPROVEMENT_PLAN.md** (1,512 lines) - Project-specific customization roadmap

### Resource Locations

All templates are in the `organized/` directory, structured by type and category for easy browsing and discovery.

## Maintenance

### Cleanup History

- **November 16, 2025**: Removed 249 duplicate files (50% size reduction)
  - Deleted duplicate top-level directories (agents/, commands/, hooks/, skills/, templates/)
  - Kept organized library with all resources
  - Result: 499 files to 250 files, 5.5MB to 2.8MB

### Guidelines

1. All resources are in `organized/` directory
2. Documentation files stay in root (`INDEX.md`, `QUICK_START.md`, `IMPROVEMENT_PLAN.md`)
3. Active skills/hooks/commands go in parent `.claude/` directory
4. Never duplicate resources - use `cp` or symlinks to install

## Next Steps

1. Review `IMPROVEMENT_PLAN.md` for project-specific recommendations
2. Install Phase 1 skills (excel-export-validator, python-testing-patterns, etc.)
3. Configure hooks for automated workflow improvements
4. Create custom commands for repetitive tasks

## Related Files

- [.claude/skills/](..//skills/) - Active skills for this project
- [.claude/commands/](..//commands/) - Active slash commands
- [.claude/hooks/](..//hooks/) - Active lifecycle hooks (if configured)
- [CLAUDE.md](../../CLAUDE.md) - Main project context for Claude Code
