# Master Claude Code Repository - Central Hub

**Purpose**: Single source of truth for Claude Code configurations across all projects
**Strategy**: Centralize, standardize, then customize per-project
**Benefit**: Maintain consistency, share improvements, faster project setup

---

## Repository Structure

```
claude-code-master/
├── README.md                           # Quick start guide
├── SELECTION_GUIDE.md                  # How to choose resources
├── SYNC_GUIDE.md                       # Keep projects updated
│
├── core/                               # Universal resources (all projects)
│   ├── skills/
│   │   ├── testing/
│   │   │   ├── tdd-enforcement.md      # TDD for any language
│   │   │   ├── systematic-testing.md   # Test patterns
│   │   │   └── coverage-requirements.md # Coverage standards
│   │   ├── debugging/
│   │   │   ├── systematic-debugging.md # 4-phase framework
│   │   │   └── root-cause-analysis.md  # Debugging methodology
│   │   ├── code-quality/
│   │   │   ├── verification-before-completion.md
│   │   │   ├── code-review-excellence.md
│   │   │   └── refactoring-patterns.md
│   │   └── git/
│   │       ├── commit-conventions.md    # Conventional commits
│   │       ├── pr-workflow.md           # Pull request standards
│   │       └── branch-strategy.md       # Git flow
│   │
│   ├── hooks/
│   │   ├── pre_tool_use.py             # Universal pre-tool hook
│   │   ├── post_tool_use.py            # Universal post-tool hook
│   │   └── session_start.py            # Session initialization
│   │
│   ├── commands/
│   │   ├── /run-tests                  # Standard test command
│   │   ├── /deploy-check               # Pre-deployment validation
│   │   ├── /code-review                # Code review workflow
│   │   └── /refactor                   # Refactoring workflow
│   │
│   └── agents/
│       ├── code-reviewer.md            # Universal code reviewer
│       ├── refactoring-expert.md       # Refactoring specialist
│       └── testing-qa-engineer.md      # QA specialist
│
├── stacks/                             # Tech stack-specific resources
│   ├── python-fastapi/
│   │   ├── skills/
│   │   │   ├── fastapi-testing.md
│   │   │   ├── pydantic-validation.md
│   │   │   └── async-patterns.md
│   │   ├── hooks/
│   │   │   ├── auto-format-black.py
│   │   │   ├── import-validator.py
│   │   │   └── type-checker.py
│   │   ├── commands/
│   │   │   ├── /run-uvicorn
│   │   │   └── /migrate-db
│   │   └── agents/
│   │       ├── fastapi-architect.md
│   │       └── python-performance-expert.md
│   │
│   ├── react-typescript/
│   │   ├── skills/
│   │   │   ├── react-testing.md
│   │   │   ├── typescript-patterns.md
│   │   │   └── component-design.md
│   │   ├── hooks/
│   │   │   ├── auto-format-prettier.py
│   │   │   └── eslint-checker.py
│   │   └── agents/
│   │       ├── react-architect.md
│   │       └── typescript-expert.md
│   │
│   ├── nodejs-express/
│   ├── django-rest/
│   ├── nextjs/
│   ├── vue/
│   └── dotnet-core/
│
├── domains/                            # Domain-specific resources
│   ├── data-analysis/
│   │   ├── skills/
│   │   │   ├── pandas-expert.md
│   │   │   ├── data-visualization.md
│   │   │   └── statistical-analysis.md
│   │   └── agents/
│   │       ├── data-scientist.md
│   │       └── ml-engineer.md
│   │
│   ├── excel-export/
│   │   ├── skills/
│   │   │   ├── excel-validation.md
│   │   │   ├── openpyxl-patterns.md
│   │   │   └── spreadsheet-design.md
│   │   └── agents/
│   │       └── excel-specialist.md
│   │
│   ├── ai-integration/
│   │   ├── skills/
│   │   │   ├── openai-api.md
│   │   │   ├── prompt-engineering.md
│   │   │   └── cost-optimization.md
│   │   └── agents/
│   │       ├── llm-engineer.md
│   │       └── prompt-engineer.md
│   │
│   ├── web-scraping/
│   ├── authentication/
│   ├── payment-processing/
│   ├── email-sending/
│   └── reporting/
│
├── templates/                          # Project templates
│   ├── minimal/                        # Bare minimum setup
│   │   ├── .claude/
│   │   │   ├── settings.local.json
│   │   │   ├── CLAUDE.md
│   │   │   └── skills/
│   │   │       └── (empty - select as needed)
│   │   └── README.md
│   │
│   ├── standard/                       # Standard full-stack project
│   │   ├── .claude/
│   │   │   ├── skills/
│   │   │   │   ├── testing/
│   │   │   │   ├── debugging/
│   │   │   │   └── code-quality/
│   │   │   ├── hooks/
│   │   │   ├── commands/
│   │   │   └── agents/
│   │   └── README.md
│   │
│   ├── ai-enhanced/                    # AI/ML projects
│   ├── data-processing/                # ETL/data pipelines
│   ├── saas-webapp/                    # Full SaaS application
│   └── microservices/                  # Microservices architecture
│
├── standards/                          # Company-wide standards
│   ├── commit-conventions.md           # Git commit standards
│   ├── code-review-checklist.md        # Review requirements
│   ├── testing-standards.md            # Test coverage, patterns
│   ├── documentation-standards.md      # Doc requirements
│   ├── security-standards.md           # Security requirements
│   └── deployment-standards.md         # Deployment process
│
├── scripts/                            # Automation scripts
│   ├── install.sh                      # Install to project
│   ├── sync.sh                         # Sync updates
│   ├── select.py                       # Interactive selector
│   └── validate.sh                     # Validate configuration
│
└── examples/                           # Real-world examples
    ├── customer-feedback-app/          # Your current project
    ├── ecommerce-platform/             # Example e-commerce
    ├── data-pipeline/                  # Example data processing
    └── microservices-backend/          # Example microservices
```

---

## Selection Strategy

### 1. Start with Core (Always Include)
```bash
# Every project gets:
core/skills/testing/
core/skills/debugging/
core/skills/code-quality/
core/skills/git/
core/hooks/
core/commands/
```

### 2. Add Tech Stack Resources
```bash
# Python + FastAPI project:
stacks/python-fastapi/

# React + TypeScript project:
stacks/react-typescript/

# Both (full-stack):
stacks/python-fastapi/
stacks/react-typescript/
```

### 3. Add Domain-Specific Resources
```bash
# Project with Excel export:
domains/excel-export/

# Project with AI integration:
domains/ai-integration/

# Data analysis project:
domains/data-analysis/
```

### 4. Choose Project Template
```bash
# Simple project:
templates/minimal/

# Standard full-stack:
templates/standard/

# AI-enhanced SaaS:
templates/ai-enhanced/
```

---

## Installation Process

### Option 1: Interactive Selection
```bash
# Clone master repo
git clone https://github.com/yourusername/claude-code-master.git

# Run interactive installer
cd claude-code-master
./scripts/select.py

# Answer questions:
# - Tech stack? (Python/FastAPI, React/TypeScript, etc.)
# - Domains? (Excel, AI, Data Analysis, etc.)
# - Template? (Minimal, Standard, AI-Enhanced, etc.)

# Install to your project
./scripts/install.sh --target /path/to/your/project
```

### Option 2: Manual Selection
```bash
# Copy core resources (required)
cp -r core/skills/* /your-project/.claude/skills/
cp -r core/hooks/* /your-project/.claude/hooks/
cp -r core/commands/* /your-project/.claude/commands/

# Copy tech stack resources
cp -r stacks/python-fastapi/skills/* /your-project/.claude/skills/
cp -r stacks/python-fastapi/hooks/* /your-project/.claude/hooks/

# Copy domain resources
cp -r domains/excel-export/skills/* /your-project/.claude/skills/
cp -r domains/ai-integration/agents/* /your-project/.claude/agents/
```

### Option 3: Template-Based
```bash
# Start from template
cp -r templates/ai-enhanced/.claude /your-project/

# Customize as needed
cd /your-project/.claude
# Edit CLAUDE.md, settings.local.json, etc.
```

---

## Sync Strategy

### Keep Projects Updated

```bash
# In your project directory
cd /your-project

# Pull latest from master repo
./scripts/sync.sh

# What it does:
# 1. Backs up current .claude/ folder
# 2. Pulls latest core resources
# 3. Pulls latest stack resources
# 4. Merges with your customizations
# 5. Reports conflicts for manual resolution
```

### Contribute Back to Master

```bash
# You created a great skill in your project
cd /your-project/.claude/skills/your-new-skill/

# Determine if it's:
# - Core (all projects benefit)
# - Stack-specific (Python/FastAPI projects)
# - Domain-specific (Excel export projects)

# Contribute back
git clone https://github.com/yourusername/claude-code-master.git
cp -r /your-project/.claude/skills/your-new-skill \
      claude-code-master/domains/excel-export/skills/

cd claude-code-master
git add domains/excel-export/skills/your-new-skill
git commit -m "Add new Excel validation skill"
git push

# Now all projects can benefit!
```

---

## Standards Enforcement

### Commit Convention Standard
```markdown
# standards/commit-conventions.md

All commits MUST follow Conventional Commits:

feat: Add new feature
fix: Bug fix
docs: Documentation changes
test: Test additions/changes
refactor: Code refactoring
perf: Performance improvements
chore: Build/tooling changes

Examples:
feat: Add Excel export validation skill
fix: Correct tab color for Churn Risk sheet
docs: Update CLAUDE.md with new skills
test: Add integration tests for Excel export
```

### Code Review Standard
```markdown
# standards/code-review-checklist.md

Every PR must pass:

- [ ] Tests passing (0 failures)
- [ ] Coverage >= 70%
- [ ] Type hints added
- [ ] Imports at top of file (PEP 8)
- [ ] Documentation updated
- [ ] CLAUDE.md updated if needed
- [ ] No credentials committed
- [ ] Performance acceptable
```

---

## Example: Customer Feedback Analyzer

Your current project would be configured as:

```bash
# Install from master
./scripts/install.sh \
  --target customer-feedback-app \
  --core all \
  --stacks python-fastapi,react-typescript \
  --domains excel-export,ai-integration,data-analysis \
  --template ai-enhanced

# Results in:
customer-feedback-app/.claude/
├── skills/
│   ├── testing/ (from core)
│   ├── debugging/ (from core)
│   ├── code-quality/ (from core)
│   ├── fastapi-patterns/ (from stacks/python-fastapi)
│   ├── react-patterns/ (from stacks/react-typescript)
│   ├── excel-validation/ (from domains/excel-export)
│   ├── openai-integration/ (from domains/ai-integration)
│   └── data-analysis/ (from domains/data-analysis)
├── hooks/
│   ├── auto-format-python.py (from stacks/python-fastapi)
│   ├── auto-format-typescript.py (from stacks/react-typescript)
│   └── test-reminder.py (from core)
├── commands/
│   ├── /run-tests (from core)
│   ├── /validate-excel (from domains/excel-export)
│   └── /optimize-costs (from domains/ai-integration)
└── agents/
    ├── excel-specialist.md (from domains/excel-export)
    ├── fastapi-architect.md (from stacks/python-fastapi)
    └── llm-engineer.md (from domains/ai-integration)
```

---

## Benefits

### For You
1. **Single source of truth** - All standards in one place
2. **Faster project setup** - Install in minutes, not hours
3. **Consistent quality** - Same standards across all projects
4. **Share improvements** - One project's skill benefits all
5. **Easy onboarding** - New team members get consistent experience

### For Your Team
1. **Standard workflows** - Same commands, same patterns
2. **Shared knowledge** - Skills documented centrally
3. **Best practices** - Proven patterns, not reinventing
4. **Cross-project consistency** - Familiar setup everywhere

### For Maintenance
1. **Update once, deploy everywhere** - Fix in master, sync to all
2. **Version control** - Track changes to standards
3. **Rollback capability** - Revert to previous versions
4. **Conflict detection** - Automated merge conflict detection

---

## Next Steps

### Phase 1: Create Master Repo (2 hours)
1. Create GitHub repository: `claude-code-master`
2. Set up directory structure (core, stacks, domains, templates)
3. Migrate current resources to appropriate locations
4. Write selection guide and sync scripts

### Phase 2: Extract from Customer Feedback App (1 hour)
1. Identify which resources are:
   - Core (all projects)
   - Python/FastAPI specific
   - Excel/AI/Data Analysis specific
2. Copy to master repo in correct locations
3. Test re-installation to customer-feedback-app

### Phase 3: Create Templates (1 hour)
1. Minimal template
2. Standard full-stack template
3. AI-enhanced template
4. Document template selection guide

### Phase 4: Automation Scripts (2 hours)
1. `install.sh` - Install to new project
2. `sync.sh` - Update existing project
3. `select.py` - Interactive selector
4. `validate.sh` - Validate configuration

---

## Recommended Structure for Your Use Case

Based on your Customer Feedback Analyzer:

```
claude-code-master/
├── core/               # Universal (20 resources)
├── stacks/
│   ├── python-fastapi/ (30 resources)
│   └── react-typescript/ (20 resources)
├── domains/
│   ├── excel-export/ (15 resources)
│   ├── ai-integration/ (10 resources)
│   └── data-analysis/ (10 resources)
├── templates/
│   └── ai-saas-app/ (complete setup)
└── standards/
    └── (your company standards)
```

**Total**: ~105 core resources, customizable per-project

---

**Status**: Ready to create master repository
**Time**: 6 hours total setup
**Value**: Unlimited - scales to all future projects
**ROI**: 10x faster project setup, consistent quality
