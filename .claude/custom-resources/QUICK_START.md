# Quick Start: Using Organized Resources

**You're here**: `.claude/organized/`
**Purpose**: Copy templates to create your skills/hooks/commands
**Time**: 30 minutes to create first skill

---

## What's Organized

```
organized/
├── skills/          ← 20+ professional skills by category
├── hooks/           ← 8 hook lifecycle events (Python)
├── commands/        ← 10+ slash command templates
└── INDEX.md         ← Complete navigation guide
```

---

## Quick Actions

### I Want To Create My First Skill (30 min)

**Best skill to start**: Excel Export Validator (directly useful for your project)

```bash
# 1. Create skill directory
mkdir -p .claude/skills/excel-export-validator

# 2. Copy template
cp organized/skills/excel/xlsx-processing-anthropic.md \
   .claude/skills/excel-export-validator/SKILL.md

# 3. Edit the file
# - Change description to mention your 7 view sheets
# - Add your 36-column validation
# - Add your tab color checks (RED/ORANGE/YELLOW/etc)
# - Reference your v3.9.0 Excel architecture

# 4. Test it
# Open Claude Code and say: "Validate the FTTH Excel export"
```

---

### I Want To Add Auto-Format Hook (15 min)

```bash
# 1. Look at template
cat organized/hooks/post_tool_use.py

# 2. Create your hook
# Copy the pattern, add black + isort

# 3. Configure in settings.local.json
# Add PostToolUse hook for *.py files

# 4. Test it
# Edit a Python file, it should auto-format
```

---

### I Want To Browse What's Available (10 min)

```bash
# See all testing skills
ls organized/skills/testing/

# See all hooks
ls organized/hooks/

# See all commands
ls organized/commands/

# Read navigation guide
cat organized/INDEX.md
```

---

## Top 3 Skills to Copy First

### 1. Test-Driven Development

**Why**: Enforces quality, prevents bugs
**File**: `organized/skills/testing/tdd-superpowers.md`
**Customize**: Change `npm test` to `pytest` patterns
**Test**: Say "I need to add a new feature"

### 2. Systematic Debugging

**Why**: Systematic over guessing
**File**: `organized/skills/debugging/systematic-debugging-superpowers.md`
**Customize**: Add project-specific checks
**Test**: Say "I have a bug in Excel export"

### 3. Excel Processing

**Why**: Directly applicable to your project
**File**: `organized/skills/excel/xlsx-processing-anthropic.md`
**Customize**: Add your export validation rules
**Test**: Say "Validate this Excel file"

---

## File Naming Convention

Files are named: `{skill-name}-{source}.md`

Examples:
- `tdd-superpowers.md` = TDD skill from obra/superpowers
- `xlsx-processing-anthropic.md` = XLSX skill from Anthropic
- `systematic-debugging-superpowers.md` = Debugging from superpowers

**Why**: Know where each skill came from for reference

---

## Customization Template

When copying a skill, customize these parts:

```markdown
---
name: your-skill-name
description: CRITICAL - When Claude should activate this skill
---

# Your Skill Title

## When to Use
[Update for your project]

## Process
[Update commands for your tech stack]

## Examples
[Add your project's examples]

## Verification
[Add your quality checks]
```

---

## Common Customizations

### For pytest (instead of npm test)
```bash
# Original
npm test path/to/test.test.ts

# Your project
PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python -m pytest -v
```

### For your Excel validation
```bash
# Add to XLSX skill
# Check our 7 view sheets present
# Verify 36 columns in Calculated Data
# Validate tab colors (RED/ORANGE/YELLOW/BLUE/PURPLE/GRAY)
# Test conditional formatting applied
```

### For your project structure
```bash
# Update paths
api/app/           # Your domain code
api/tests/         # Your tests
scripts/           # Your scripts
```

---

## Don't Do This

❌ **Don't edit files in organized/** - They're templates
❌ **Don't add files to organized/** - Use `.claude/` folder
❌ **Don't commit organized/** - It's 437MB reference material

✅ **Do copy from organized/** - That's what it's for
✅ **Do customize the copies** - Make them yours
✅ **Do test your skills** - Ensure they activate correctly

---

## Workflow

1. **Find**: Browse `organized/` for what you need
2. **Copy**: Copy template to `.claude/` folder
3. **Customize**: Edit for your project
4. **Test**: Verify skill activates correctly
5. **Iterate**: Refine based on usage

---

## Where to Copy Files

```
Source → Destination

organized/skills/testing/tdd.md
  → .claude/skills/test-driven-development/SKILL.md

organized/hooks/post_tool_use.py
  → .claude/hooks/auto_format.py

organized/commands/build.md
  → .claude/commands/benchmark.md
```

---

## Next Steps

Choose one:

**A. Create First Skill** (30 min)
- Copy excel validator template
- Customize for your project
- Test activation

**B. Add First Hook** (15 min)
- Copy post_tool_use.py
- Add auto-format logic
- Test on Python file edit

**C. Browse More** (15 min)
- Read INDEX.md
- Explore categories
- Plan what to implement

---

## Help

**Question**: How do I know which skill to use?
**Answer**: Read the "When to Use" section in each skill

**Question**: Can I combine multiple skills?
**Answer**: Yes! Skills can reference each other (see systematic-debugging)

**Question**: How do I test if a skill works?
**Answer**: Say the trigger phrase naturally in Claude Code

**Question**: What if I break something?
**Answer**: Just delete the skill folder and start over

---

## Summary

**Location**: `.claude/organized/`
**Contains**: 43 professional templates
**Purpose**: Copy and customize for your project
**Time**: 30 min for first skill

**Top 3**: TDD, Systematic Debugging, Excel Processing

**Next**: Copy one skill, customize it, test it

---

**Quick Command**: See all available templates
```bash
find organized/ -name "*.md" -o -name "*.py" | sort
```
