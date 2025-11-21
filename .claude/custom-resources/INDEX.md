# Custom Claude Code Resources - Customer Feedback Analyzer

**Purpose**: Complete working library of Claude Code resources for the Customer Feedback Analyzer project
**Source**: 14 curated repositories + custom project-specific resources
**Date Created**: 2025-11-16
**Total Resources**: 249 files + 5 planning documents = 254 total

---

## What This Folder Contains

This is your complete, customizable Claude Code resource library organized by functionality:

- **Skills** (122): Auto-activated expertise patterns
- **Agents** (51): Persona-based AI specialists (including 2 custom for this project)
- **Commands** (63): Slash command templates
- **Hooks** (8): Event-driven automation
- **Guides** (5): Implementation guides
- **Planning Docs** (5): Strategic planning and improvement roadmaps

---

## Directory Structure

```
custom-resources/
├── skills/ (122 skills across 20 categories)
│   ├── testing/ (8) - TDD, test patterns, coverage
│   ├── debugging/ (2) - Systematic debugging, root cause analysis
│   ├── code-quality/ (21) - Code review, verification, best practices
│   ├── excel/ (1) - Excel/XLSX processing and generation
│   ├── documents/ (3) - DOCX, PDF, PPTX processing
│   ├── data-analysis/ (3) - Data analysis, feedback processing
│   ├── git/ (4) - Git workflows, branching, PR management
│   ├── deployment/ (10) - CI/CD, migrations, Docker
│   ├── security/ (1) - Security scanning, SAST
│   ├── design/ (6) - UI/UX, frontend, brand guidelines
│   ├── business/ (11) - Pitch decks, SEO, analytics
│   ├── development/ (14) - Python, JS, API, backend patterns
│   ├── infrastructure/ (13) - Cloud, Kubernetes, observability
│   ├── templates/ (6) - Skill creation, MCP builders
│   ├── database/ (2) - PostgreSQL, SQL optimization
│   ├── payment-processing/ (4) - Stripe, PayPal, PCI compliance
│   ├── llm-development/ (4) - LangChain, RAG, prompt engineering
│   ├── blockchain/ (3) - DeFi, Solidity, NFT standards
│   ├── lifestyle/ (3) - Personal productivity
│   └── writing/ (3) - Content creation
│
├── agents/ (51 persona-based specialists)
│   ├── engineering/ (26) - Senior engineers by specialty + claudekit experts
│   ├── compliance/ (12) - QMS, regulatory, GDPR
│   ├── product/ (6) - PM, product strategist, UX
│   ├── marketing/ (3) - Content, demand gen, strategy
│   ├── c-level/ (2) - CEO, CTO advisors
│   ├── excel/ (1) - **CUSTOM: Excel export specialist for this project**
│   └── testing/ (1) - **CUSTOM: pytest + FastAPI specialist for this project**
│
├── commands/ (63 slash command templates)
│   ├── anthropic/ - Official Anthropic commands
│   ├── architecture/ - Architecture analysis
│   ├── cleanup/ - Code cleanup
│   ├── documentation/ - Documentation generation
│   ├── git/ - Git workflow commands
│   ├── product-management/ - Product management
│   ├── prompt-engineering/ - Prompt engineering
│   ├── refactor/ - Refactoring workflows
│   ├── security/ - Security scanning
│   ├── usage-tracking/ - Usage analytics
│   └── workflow/ - General workflow commands
│
├── hooks/ (8 lifecycle events)
│   ├── user_prompt_submit.py - Before user input
│   ├── pre_tool_use.py - Before tool execution
│   ├── post_tool_use.py - After tool completes
│   ├── stop.py - When agent stops
│   ├── subagent_stop.py - When subagent finishes
│   ├── pre_compact.py - Before context compaction
│   ├── session_start.py - Session initialization
│   └── notification.py - System notifications
│
├── guides/ (5 implementation guides)
│   └── (Setup and usage guides)
│
├── templates/ (Empty - ready for custom templates)
│
└── Planning Documents (5 strategic files)
    ├── IMPROVEMENT_PLAN.md (38KB) - 3-phase implementation roadmap
    ├── MASTER_REPO_PLAN.md (15KB) - Central repository strategy
    ├── INDEX.md (This file) - Resource navigation
    ├── QUICK_START.md - Quick start guide
    └── README.md - Overview and instructions
```

---

## Custom Resources for This Project

### Excel Export Specialist (CUSTOM)

**Location**: `agents/excel/excel-export-specialist.md`

**Purpose**: Expert in Customer Feedback Analyzer Excel export architecture

**Expertise**:
- v3.9.0 Modern Excel Builder (7 view sheets + Calculated Data)
- 36-column calculated data schema
- Professional tab colors (RED/ORANGE/YELLOW/BLUE/PURPLE/GRAY)
- Conditional formatting rules
- openpyxl library expertise

**When to use**: Excel export modifications, debugging, or validation

---

### Pytest + FastAPI Testing Specialist (CUSTOM)

**Location**: `agents/testing/pytest-fastapi-specialist.md`

**Purpose**: Expert in testing the Customer Feedback Analyzer with pytest + FastAPI

**Expertise**:
- pytest testing framework (70%+ coverage target)
- FastAPI endpoint testing (TestClient)
- Async testing (@pytest.mark.asyncio)
- Test fixtures and mocking
- Coverage reporting (HTML, XML, JSON, terminal)

**When to use**: Writing tests, debugging test failures, improving coverage

---

## Quick Navigation by Use Case

### Excel Processing & Validation

**Problem**: Need to validate Excel exports with 7 view sheets, 36 columns, tab colors

**Resources**:
1. `skills/excel/xlsx-processing-anthropic.md` - Base Excel processing patterns
2. `agents/excel/excel-export-specialist.md` - **CUSTOM: Project-specific expert**
3. Reference: `IMPROVEMENT_PLAN.md` → Phase 1 → Excel Export Validator skill

**Next Step**: Copy excel skill to `.claude/skills/excel-export-validator/SKILL.md`

---

### Testing & TDD Workflow

**Problem**: Need systematic testing for FastAPI backend

**Resources**:
1. `skills/testing/tdd-superpowers.md` - RED-GREEN-REFACTOR TDD
2. `skills/testing/python-testing-patterns-wshobson.md` - Python pytest patterns
3. `agents/testing/pytest-fastapi-specialist.md` - **CUSTOM: Project-specific expert**
4. `/run-tests` command - Already implemented in project

**Next Step**: Copy TDD skill to `.claude/skills/test-driven-development/SKILL.md`

---

### Debugging Systematically

**Problem**: Need structured approach to debugging issues

**Resources**:
1. `skills/debugging/systematic-debugging-superpowers.md` - 4-phase debugging framework
2. `skills/debugging/root-cause-tracing-superpowers.md` - Backward tracing
3. Reference: `IMPROVEMENT_PLAN.md` → Phase 1 → Systematic Debugging skill

**Next Step**: Copy debugging skill to `.claude/skills/systematic-debugging/SKILL.md`

---

### Code Quality & Verification

**Problem**: Ensure fixes work before marking tasks complete

**Resources**:
1. `skills/code-quality/verification-before-completion-superpowers.md` - Verification patterns
2. `skills/code-quality/code-review-excellence-wshobson.md` - Code review best practices
3. Reference: `IMPROVEMENT_PLAN.md` → Phase 1 → Verification Before Completion skill

**Next Step**: Copy verification skill to `.claude/skills/verification-before-completion/SKILL.md`

---

### Import Quality (Python)

**Problem**: Enforce PEP 8 import standards, prevent lazy imports

**Resources**:
1. Reference: CLAUDE.md → Import Standards section
2. Reference: `IMPROVEMENT_PLAN.md` → Phase 1 → Import Quality Enforcer skill
3. Reference: `IMPROVEMENT_PLAN.md` → Phase 2 → Import Validation Hook

**Next Step**: Create custom skill based on project standards

---

### Data Analysis & Feedback Processing

**Problem**: Analyze customer feedback datasets

**Resources**:
1. `skills/data-analysis/data-analyst-ailabs.md` - Professional data analysis
2. `skills/data-analysis/csv-data-visualizer-ailabs.md` - CSV visualization
3. `/analyze-feedback` command - Already implemented in project

**Next Step**: Copy data analysis skill and customize for FTTH telecom domain

---

### Deployment & CI/CD

**Problem**: Need deployment automation and validation

**Resources**:
1. `skills/deployment/github-actions-templates-wshobson.md` - GitHub Actions
2. `skills/deployment/docker-containerization-ailabs.md` - Docker patterns
3. Reference: `IMPROVEMENT_PLAN.md` → Phase 3 → /deploy-check command

**Next Step**: Set up GitHub Actions workflow

---

## Planning Documents

### IMPROVEMENT_PLAN.md (38KB)

**Purpose**: Complete 3-phase implementation roadmap for custom Claude Code setup

**Contents**:
- **Phase 1**: 6 core skills (Excel validator, TDD, debugging, import quality, verification, code review)
- **Phase 2**: 5 automation hooks (auto-format, import validation, test reminder, coverage update, Excel test trigger)
- **Phase 3**: 8 custom commands (/benchmark, /deploy-check, /validate-excel, etc.)

**Expected ROI**: $39,342/year in time and cost savings

**Status**: Ready to implement

---

### MASTER_REPO_PLAN.md (15KB)

**Purpose**: Architecture for central Claude Code repository across all projects

**Strategy**:
1. Build complete custom-resources in current project (this folder)
2. Test and iterate on real project
3. Later extract to master repository for cross-project use

**Structure**:
```
claude-code-master/
├── core/ - Universal resources (all projects)
├── stacks/ - Tech stack-specific (python-fastapi, react-typescript)
├── domains/ - Domain-specific (excel-export, ai-integration, data-analysis)
├── templates/ - Project templates (minimal, standard, ai-enhanced)
├── standards/ - Company-wide standards
└── scripts/ - Automation (install.sh, sync.sh, select.py)
```

**Status**: Strategic plan for future scaling

---

## How to Use This Library

### Phase 1: Start with One Skill (30 minutes)

**Recommended First Skill**: Excel Export Validator

1. **Read the template**:
   ```bash
   cat custom-resources/skills/excel/xlsx-processing-anthropic.md
   ```

2. **Create active skill**:
   ```bash
   mkdir -p .claude/skills/excel-export-validator
   cp custom-resources/skills/excel/xlsx-processing-anthropic.md \
      .claude/skills/excel-export-validator/SKILL.md
   ```

3. **Customize for project**:
   - Add 7 view sheets requirement
   - Add 36 columns validation
   - Add tab color checks (RED/ORANGE/YELLOW/BLUE/PURPLE/GRAY)
   - Add conditional formatting validation
   - Reference: See `custom-resources/agents/excel/excel-export-specialist.md` for requirements

4. **Test activation**:
   Say to Claude: "Validate the Excel export for the FTTH dataset"

---

### Phase 2: Add Automation Hooks (1 hour)

**Recommended First Hook**: Auto-format Python files

1. **Review template**:
   ```bash
   cat custom-resources/hooks/post_tool_use.py
   ```

2. **Create custom hook**:
   ```bash
   cat > .claude/hooks/auto_format_python.py << 'EOF'
   from claude_code import Hook

   class AutoFormatPython(Hook):
       event = "PostToolUse"

       async def run(self, context):
           if context.tool == "Edit" and context.file_path.endswith(".py"):
               # Run black + isort
               await context.bash("black", context.file_path)
               await context.bash("isort", context.file_path)
   EOF
   ```

3. **Test**: Edit a Python file and watch auto-formatting

---

### Phase 3: Create Custom Commands (2 hours)

**Recommended First Command**: /validate-excel

1. **Review templates**:
   ```bash
   ls custom-resources/commands/
   ```

2. **Create command**:
   ```bash
   cat > .claude/commands/validate-excel.md << 'EOF'
   # Excel Export Validation Command

   Run comprehensive Excel export validation:

   1. Check sheet count (7 view sheets + Calculated Data)
   2. Verify column count (36 in Calculated Data)
   3. Validate tab colors (RED/ORANGE/YELLOW/BLUE/PURPLE/GRAY)
   4. Run integration tests
   5. Visual inspection checklist

   Commands to run:
   ```bash
   cd api
   PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest \
     api/tests/domain/export/excel/ -v
   ```
   EOF
   ```

3. **Test**: Type `/validate-excel` in Claude Code

---

## Skills by Category (122 Total)

### Testing (8 skills)

**From obra/superpowers**:
- `tdd-superpowers.md` - RED-GREEN-REFACTOR enforced TDD
- `testing-anti-patterns-superpowers.md` - Common testing mistakes
- `testing-skills-with-subagents-superpowers.md` - Testing skill quality
- `condition-based-waiting-superpowers.md` - Async testing patterns

**From wshobson**:
- `e2e-testing-patterns-wshobson.md` - End-to-end testing
- `python-testing-patterns-wshobson.md` - Python pytest patterns
- `javascript-testing-patterns-wshobson.md` - JavaScript testing
- `bats-testing-patterns-wshobson.md` - Bash testing

**From ailabs**:
- `webapp-testing-anthropic.md` - Web app testing

**From Anthropic**:
- (Official testing patterns)

---

### Debugging (2 skills)

**From obra/superpowers**:
- `systematic-debugging-superpowers.md` - 4-phase debugging framework

**From wshobson**:
- `debugging-strategies-wshobson.md` - General debugging strategies

---

### Code Quality (21 skills)

**From obra/superpowers (11 skills)**:
- `verification-before-completion-superpowers.md` - Ensure fixes work
- `requesting-code-review-superpowers.md` - Code review workflow
- `receiving-code-review-superpowers.md` - Responding to reviews
- `subagent-driven-development-superpowers.md` - Fast iteration
- `brainstorming-superpowers.md` - Interactive design
- `writing-plans-superpowers.md` - Implementation planning
- `executing-plans-superpowers.md` - Batch execution
- `dispatching-parallel-agents-superpowers.md` - Multi-agent coordination
- `writing-skills-superpowers.md` - Creating new skills
- `sharing-skills-superpowers.md` - Contributing skills
- `using-superpowers-superpowers.md` - Orientation guide

**From wshobson**:
- `code-review-excellence-wshobson.md` - Code review best practices
- `error-handling-patterns-wshobson.md` - Error handling strategies
- (8 more code quality patterns)

**From ailabs**:
- `codebase-documenter-ailabs.md` - Documentation generation
- `tech-debt-analyzer-ailabs.md` - Technical debt assessment

---

### Excel Processing (1 skill)

**From Anthropic (official)**:
- `xlsx-processing-anthropic.md` - Comprehensive Excel creation/editing/analysis

**CRITICAL FOR THIS PROJECT**: Directly applicable to Excel export feature

---

### Documents (3 skills)

**From Anthropic (official)**:
- `docx-processing-anthropic.md` - Microsoft Word (.docx) creation/editing
- `pdf-processing-anthropic.md` - PDF generation and manipulation
- `pptx-processing-anthropic.md` - PowerPoint (.pptx) creation

---

### Data Analysis (3 skills)

**From ailabs**:
- `data-analyst-ailabs.md` - Professional data analysis workflows
- `business-analytics-reporter-ailabs.md` - Business reporting
- `csv-data-visualizer-ailabs.md` - CSV data visualization

**Applicable to**: FTTH customer feedback analysis, sentiment analysis

---

### Development (14 skills)

**Backend & API**:
- `fastapi-templates-wshobson.md` - FastAPI scaffolding
- `api-design-principles-wshobson.md` - API design patterns
- `architecture-patterns-wshobson.md` - Software architecture
- `microservices-patterns-wshobson.md` - Microservices design

**Python**:
- `async-python-patterns-wshobson.md` - Async Python
- `python-packaging-wshobson.md` - Python package management
- `python-performance-optimization-wshobson.md` - Performance tuning

**JavaScript/TypeScript**:
- `modern-javascript-patterns-wshobson.md` - Modern JS patterns
- `typescript-advanced-types-wshobson.md` - TypeScript types

**Shell**:
- `bash-defensive-patterns-wshobson.md` - Defensive bash scripting
- `shellcheck-configuration-wshobson.md` - Shell linting

---

### Infrastructure (13 skills)

**Cloud**:
- `cost-optimization-wshobson.md` - Cloud cost management
- `terraform-module-library-wshobson.md` - Terraform modules
- `multi-cloud-architecture-wshobson.md` - Multi-cloud patterns

**Kubernetes**:
- `gitops-workflow-wshobson.md` - GitOps with Kubernetes
- `helm-chart-scaffolding-wshobson.md` - Helm charts
- `k8s-manifest-generator-wshobson.md` - K8s manifests
- `k8s-security-policies-wshobson.md` - K8s security

**Observability**:
- `distributed-tracing-wshobson.md` - Distributed tracing
- `grafana-dashboards-wshobson.md` - Grafana dashboards
- `slo-implementation-wshobson.md` - SLO/SLI implementation
- `prometheus-configuration-wshobson.md` - Prometheus setup

---

### Deployment (10 skills)

**CI/CD**:
- `deployment-pipeline-design-wshobson.md` - Pipeline design
- `github-actions-templates-wshobson.md` - GitHub Actions
- `gitlab-ci-patterns-wshobson.md` - GitLab CI
- `secrets-management-wshobson.md` - Secrets management
- `cicd-pipeline-generator-ailabs.md` - CI/CD generation

**Migrations**:
- `database-migration-wshobson.md` - Database migrations
- `dependency-upgrade-wshobson.md` - Dependency upgrades
- `react-modernization-wshobson.md` - React modernization

---

### Git Workflows (4 skills)

**From obra/superpowers**:
- `using-git-worktrees-superpowers.md` - Parallel branch management
- `finishing-a-development-branch-superpowers.md` - Merge/PR decisions

**From wshobson**:
- `git-advanced-workflows-wshobson.md` - Advanced Git workflows
- `monorepo-management-wshobson.md` - Monorepo strategies

---

### Security (1 skill)

**From wshobson**:
- `sast-configuration-wshobson.md` - Static application security testing

---

### Design (6 skills)

**From Anthropic**:
- `brand-guidelines-anthropic.md` - Brand guidelines creation
- `canvas-design-anthropic.md` - Canvas-based design
- `frontend-design-anthropic.md` - Frontend design patterns
- `theme-factory-anthropic.md` - Theme generation

**From ailabs**:
- `frontend-enhancer-ailabs.md` - Frontend enhancement
- (1 more design skill)

---

### Business (11 skills)

**From Anthropic**:
- `internal-comms-anthropic.md` - Internal communications

**From ailabs**:
- `pitch-deck-ailabs.md` - Pitch deck creation
- `business-document-generator-ailabs.md` - Business docs
- `brand-analyzer-ailabs.md` - Brand analysis
- `finance-manager-ailabs.md` - Financial management
- `startup-validator-ailabs.md` - Startup validation
- `seo-optimizer-ailabs.md` - SEO optimization
- `social-media-generator-ailabs.md` - Social media content
- (3 more business skills)

---

### Templates (6 skills)

**From Anthropic (skill creation tools)**:
- `skill-creator-anthropic.md` - Create new skills
- `template-skill-anthropic.md` - Skill template
- `mcp-builder-anthropic.md` - MCP server builder
- `artifacts-builder-anthropic.md` - Artifact builder
- `slack-gif-creator-anthropic.md` - Slack GIF automation
- `algorithmic-art-anthropic.md` - Algorithmic art generation

---

### Database (2 skills)

**From wshobson**:
- `postgresql-wshobson.md` - PostgreSQL design patterns
- `sql-optimization-patterns-wshobson.md` - SQL query optimization

---

### Payment Processing (4 skills)

**From wshobson**:
- `billing-automation-wshobson.md` - Automated billing
- `paypal-integration-wshobson.md` - PayPal integration
- `pci-compliance-wshobson.md` - PCI compliance
- `stripe-integration-wshobson.md` - Stripe integration

---

### LLM Development (4 skills)

**From wshobson**:
- `langchain-architecture-wshobson.md` - LangChain app architecture
- `llm-evaluation-wshobson.md` - LLM evaluation strategies
- `prompt-engineering-patterns-wshobson.md` - Prompt engineering
- `rag-implementation-wshobson.md` - RAG (Retrieval Augmented Generation)

---

### Blockchain (3 skills)

**From wshobson**:
- `defi-protocol-templates-wshobson.md` - DeFi protocol scaffolding
- `solidity-security-wshobson.md` - Solidity security patterns
- `nft-standards-wshobson.md` - NFT standard implementations

---

### Lifestyle (3 skills)

- Personal productivity and wellness patterns

---

### Writing (3 skills)

- Content creation and writing assistance

---

## Agents by Category (51 Total)

### Engineering Team (26 agents)

**From alirezarezvani (Senior Engineering Roles)**:
- `senior-backend-alirezarezvani.md` - Senior backend engineer
- `senior-frontend-alirezarezvani.md` - Senior frontend engineer
- `senior-fullstack-alirezarezvani.md` - Senior fullstack engineer
- `senior-architect-alirezarezvani.md` - Software architect
- `senior-devops-alirezarezvani.md` - DevOps engineer
- `senior-data-engineer-alirezarezvani.md` - Data engineer
- `senior-data-scientist-alirezarezvani.md` - Data scientist
- `senior-ml-engineer-alirezarezvani.md` - ML engineer
- `senior-prompt-engineer-alirezarezvani.md` - Prompt engineer
- `senior-computer-vision-alirezarezvani.md` - Computer vision
- `senior-qa-alirezarezvani.md` - QA engineer
- `senior-security-alirezarezvani.md` - Security engineer
- `senior-secops-alirezarezvani.md` - SecOps engineer
- `code-reviewer-alirezarezvani.md` - Code reviewer

**From claudekit (Domain Experts)**:
- `ai-sdk-expert-claudekit.md` - AI SDK expertise
- `cli-expert-claudekit.md` - CLI development
- `code-review-expert-claudekit.md` - Code review
- `code-search-claudekit.md` - Code search
- `nestjs-expert-claudekit.md` - NestJS expertise
- `oracle-claudekit.md` - Oracle specialist
- `refactoring-expert-claudekit.md` - Refactoring
- `research-expert-claudekit.md` - Research
- `triage-expert-claudekit.md` - Issue triage

**From templates**:
- `code-searcher-template.md` - Code search template
- `get-current-datetime-template.md` - Datetime utility
- `memory-bank-synchronizer-template.md` - Memory sync

**When to use**: Specialized engineering expertise for complex technical tasks

---

### Excel & Testing (2 agents) - **CUSTOM FOR THIS PROJECT**

**Excel Specialist**:
- `excel-export-specialist.md` - Expert in v3.9.0 Modern Excel Builder
- Knows 7 view sheets, 36 columns, tab colors, conditional formatting
- **Created specifically for Customer Feedback Analyzer**

**Testing Specialist**:
- `pytest-fastapi-specialist.md` - Expert in pytest + FastAPI testing
- Knows FastAPI TestClient, async testing, coverage reporting
- **Created specifically for Customer Feedback Analyzer**

**When to use**: Excel export work or testing tasks in this project

---

### Compliance & Quality (12 agents)

**From alirezarezvani (Regulatory & Quality Management)**:
- `quality-manager-qms-iso13485-alirezarezvani.md` - ISO 13485 QMS
- `quality-manager-qmr-alirezarezvani.md` - Quality manager
- `regulatory-affairs-head-alirezarezvani.md` - Regulatory affairs
- `qms-audit-expert-alirezarezvani.md` - QMS auditing
- `isms-audit-expert-alirezarezvani.md` - ISMS auditing
- `quality-documentation-manager-alirezarezvani.md` - Documentation
- `capa-officer-alirezarezvani.md` - CAPA management
- `risk-management-specialist-alirezarezvani.md` - Risk management
- `fda-consultant-specialist-alirezarezvani.md` - FDA compliance
- `mdr-745-specialist-alirezarezvani.md` - MDR 745/2017 specialist
- `gdpr-dsgvo-expert-alirezarezvani.md` - GDPR expert
- `information-security-manager-iso27001-alirezarezvani.md` - ISO 27001

**When to use**: Compliance, auditing, regulatory affairs for regulated industries

---

### Product Team (6 agents)

**From alirezarezvani (Product Management)**:
- `product-manager-toolkit-alirezarezvani.md` - Product manager
- `product-strategist-alirezarezvani.md` - Product strategist
- `agile-product-owner-alirezarezvani.md` - Agile product owner
- `ux-researcher-designer-alirezarezvani.md` - UX research & design
- `ui-design-system-alirezarezvani.md` - UI design system

**From templates**:
- `ux-design-expert-template.md` - UX design template

**When to use**: Product strategy, UX research, design system work

---

### Marketing (3 agents)

**From alirezarezvani (Marketing Specialists)**:
- `marketing-strategy-pmm-alirezarezvani.md` - Product marketing
- `marketing-demand-acquisition-alirezarezvani.md` - Demand generation
- `content-creator-alirezarezvani.md` - Content creation

**When to use**: Marketing strategy, content creation, demand generation

---

### C-Level Advisors (2 agents)

**From alirezarezvani (Executive Advisors)**:
- `ceo-advisor-alirezarezvani.md` - CEO strategic advisor
- `cto-advisor-alirezarezvani.md` - CTO technical advisor

**When to use**: Strategic planning, executive decision-making

---

## Commands by Category (63 Total)

### Anthropic Commands

Official Anthropic slash command templates

### Architecture Commands

- Architecture analysis
- System design

### Cleanup Commands

- Code cleanup workflows

### Documentation Commands

- Documentation generation
- README updates

### Git Commands

- Git workflow automation
- Branch management
- PR workflows

### Product Management Commands

- Product planning
- Feature tracking

### Prompt Engineering Commands

- Prompt optimization
- LLM interaction patterns

### Refactor Commands

- Code refactoring workflows
- Quality improvement

### Security Commands

- Security scanning
- Vulnerability detection

### Usage Tracking Commands

- Conversation analysis
- Usage metrics

### Workflow Commands

- General workflow automation
- Task orchestration

---

## Hooks (8 Lifecycle Events)

All 8 Claude Code lifecycle events are available as Python hook templates:

| Hook File | Event | Purpose |
|-----------|-------|---------|
| `user_prompt_submit.py` | UserPromptSubmit | Before user input processed |
| `pre_tool_use.py` | PreToolUse | Before tool execution |
| `post_tool_use.py` | PostToolUse | After tool completes |
| `stop.py` | Stop | When agent stops |
| `subagent_stop.py` | SubagentStop | When subagent finishes |
| `pre_compact.py` | PreCompact | Before context compaction |
| `session_start.py` | SessionStart | Session initialization |
| `notification.py` | Notification | System notifications |

**Source**: disler/claude-code-hooks-mastery

**Example Use Cases**:
- Auto-format Python files (post_tool_use.py)
- Validate imports (post_tool_use.py)
- Security scanning (pre_tool_use.py)
- Session context setup (session_start.py)

---

## Recommended Implementation Order

### Phase 1: Core Skills (2 hours)

**Priority Order**:

1. **Excel Export Validator** (30 min)
   - Copy: `skills/excel/xlsx-processing-anthropic.md`
   - Customize: Add 7 view sheets, 36 columns, tab colors
   - Activate: "Validate the Excel export"

2. **TDD Enforcer** (30 min)
   - Copy: `skills/testing/tdd-superpowers.md`
   - Customize: pytest commands, FastAPI patterns
   - Activate: "Write tests first"

3. **Systematic Debugging** (30 min)
   - Copy: `skills/debugging/systematic-debugging-superpowers.md`
   - Customize: Excel validation, schema checks
   - Activate: "Debug this issue systematically"

4. **Verification Before Completion** (30 min)
   - Copy: `skills/code-quality/verification-before-completion-superpowers.md`
   - Customize: Excel tests, integration tests
   - Activate: "Verify this fix works"

---

### Phase 2: Automation Hooks (1-2 hours)

**Priority Order**:

1. **Auto-format Python** (30 min)
   - Template: `hooks/post_tool_use.py`
   - Customize: black + isort on Python file edits

2. **Import Validation** (30 min)
   - Template: `hooks/post_tool_use.py`
   - Customize: pyflakes check on Python files

3. **Test Reminder** (30 min)
   - Template: `hooks/post_tool_use.py`
   - Customize: Remind to run tests after logic changes

---

### Phase 3: Custom Commands (2 hours)

**Priority Order**:

1. **/validate-excel** (30 min)
   - Excel export validation workflow

2. **/deploy-check** (30 min)
   - Pre-deployment validation

3. **/benchmark** (30 min)
   - Performance benchmarking

4. **/optimize-costs** (30 min)
   - OpenAI API cost analysis

---

## Work In This Folder

**THIS IS YOUR WORKING LIBRARY** - Feel free to:

- Add new skills/agents/commands/hooks
- Modify existing resources for your needs
- Create project-specific documentation
- Experiment with different patterns

**Guidelines**:

1. **Keep organized by category** - Maintain the folder structure
2. **Mark custom resources** - Add "CUSTOM:" prefix to descriptions
3. **Document changes** - Update this INDEX when adding resources
4. **Test before using** - Verify resources work in your project

---

## Relationship to Other Folders

### .claude/external-examples/

- Original repositories (14 repos, 437MB)
- Organized by repository name
- Complete with READMEs and documentation
- **Use when**: Need to see original context or full documentation

### .claude/organized/

- Source material for custom-resources
- Organized by functionality (not repository)
- 247 resources from 14 repositories
- **Use when**: Finding templates to copy to custom-resources

### .claude/custom-resources/ (THIS FOLDER)

- Working library for this project
- Customizable resources
- Includes 2 project-specific agents
- **Use when**: Building your Claude Code configuration

---

## Next Steps

### Immediate (Next 30 minutes)

1. **Read IMPROVEMENT_PLAN.md** - Understand the 3-phase strategy
2. **Copy first skill** - Excel Export Validator (most critical)
3. **Test activation** - Say "Validate the Excel export"

### Short-term (Next week)

1. **Implement Phase 1 skills** (6 skills, 2 hours)
2. **Add Phase 2 hooks** (5 hooks, 2 hours)
3. **Test workflow improvements** (1 hour)

### Long-term (Next month)

1. **Complete Phase 3 commands** (8 commands, 2 hours)
2. **Measure ROI** - Track time savings
3. **Extract to master repo** - See MASTER_REPO_PLAN.md

---

## Quality & Sources

**Total Resources**: 249 files + 5 planning docs = 254 total

**Quality**: Enterprise-grade, production-tested resources from:
- Official Anthropic (16 resources)
- obra/superpowers (20 high-quality skills)
- wshobson enterprise patterns (59 plugin-based skills)
- ailabs business automation (23 skills)
- alirezarezvani production agents (50 agents)
- claudekit domain experts (12 agents)
- Custom for this project (2 agents, 5 planning docs)

**Coverage**:
- All major programming languages (Python, JavaScript, TypeScript, Solidity, Shell)
- All major frameworks (FastAPI, React, Angular, LangChain, Kubernetes)
- All major cloud platforms (AWS, Azure, GCP, multi-cloud)
- All major document formats (DOCX, PDF, PPTX, XLSX)
- Full software lifecycle (development, testing, deployment, observability)
- Business & compliance (product, marketing, regulatory, quality)

---

## Summary

**What**: Complete working library of Claude Code resources for Customer Feedback Analyzer
**Where**: `.claude/custom-resources/`
**Why**: Faster development, better quality, consistent patterns
**How**: Copy templates, customize, test

**Resources**:
- Skills: 122 (20 categories)
- Agents: 51 (6 categories, including 2 custom)
- Commands: 63 (11 categories)
- Hooks: 8 (all lifecycle events)
- Guides: 5
- Planning: 5 strategic documents

**Expected ROI**: $39,342/year (80-120 hours/month time savings + cost reductions)

**Status**: COMPLETE - Ready to implement Phase 1
**Next**: Copy first skill (Excel Export Validator)
**Time to First Skill**: 30 minutes

---

**Last Updated**: 2025-11-16
**Total Files**: 254 (249 resources + 5 planning docs)
**Repository Sources**: 14 curated GitHub repositories
**Custom Resources**: 2 project-specific agents + 5 planning documents
