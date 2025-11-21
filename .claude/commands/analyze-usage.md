---
description: Export and analyze Claude Code conversations for configuration insights
---

# Analyze Claude Code Usage Patterns

This command exports your Claude Code conversation history and generates actionable insights for improving your configuration.

## What it does:

1. Exports all conversations to JSON and Markdown formats
2. Analyzes tool usage patterns
3. Identifies frequently used commands
4. Detects common errors and pain points
5. Generates suggestions for:
   - Missing permissions to add
   - New slash commands to create
   - Hooks to implement
   - CLAUDE.md improvements

## Running the analysis:

!PYTHONPATH=".:$PYTHONPATH" ./venv/Scripts/python scripts/analysis/export_claude_conversations.py --all

## Output files:

The analysis creates a `claude_conversations_export/` directory with:

- `conversations_*.json` - Full conversation data
- `conversations_*.md` - Readable conversation transcripts
- `insights_*.json` - Detailed usage statistics
- `suggestions_*.md` - **Action items for improving config**

## Next steps:

1. Review the suggestions file:
   - Open `claude_conversations_export/suggestions_*.md`

2. Apply recommendations:
   - Update `.claude/settings.local.json` with suggested permissions
   - Create new slash commands in `.claude/commands/`
   - Add suggested hooks
   - Enhance `CLAUDE.md` documentation

3. Track improvements:
   - Re-run this command monthly
   - Compare insights over time
   - Measure configuration effectiveness

## For detailed documentation:

See: `scripts/analysis/README_CONVERSATION_EXPORT.md`
