# MCP Server Configurations

Model Context Protocol (MCP) servers provide enhanced capabilities for Claude Code.

## Available Servers

### 1. Filesystem Server (datasets/)

**Purpose:** Direct access to datasets without manual upload

**Configuration:** [filesystem-server.json](filesystem-server.json)

**Usage:**
```
User: Analyze FTTH_846.csv

Claude uses Filesystem MCP to:
1. Read datasets/telecom/FTTH_846.csv directly
2. Preview first 100 rows
3. Detect schema automatically
4. Run analysis
(No manual upload needed!)
```

**Benefits:**
- Skip upload step (5 minutes saved per analysis)
- Faster iteration on datasets
- Direct file access from Claude Code

**Setup:**
```bash
# MCP server runs automatically when configured
# No additional installation needed
```

### 2. GitHub Server (Future - Phase 2)

**Purpose:** Enhanced PR/issue management

**Planned Features:**
- Create PRs with templates
- Add reviewers automatically
- Link related issues
- Update project boards
- Post comments

**Status:** Planned for Phase 2 implementation

## Installation

### Option 1: Configure in Claude Code Settings

Add to `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "filesystem-datasets": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "datasets/"
      ]
    }
  }
}
```

### Option 2: Use Separate Config Files

Reference config files in settings:

```json
{
  "mcpServers": {
    "$ref": ".claude/mcp/filesystem-server.json#/mcpServers"
  }
}
```

## Testing

```bash
# Test filesystem access
# In Claude Code session:
User: List files in datasets/telecom/

# Should see FTTH_846.csv and other datasets
```

## Troubleshooting

### Server Not Starting

1. Check Node.js installed:
   ```bash
   node --version  # Should be 18.x or higher
   ```

2. Check npm/npx available:
   ```bash
   npx --version
   ```

3. Verify config syntax:
   ```bash
   # Validate JSON
   python -m json.tool .claude/mcp/filesystem-server.json
   ```

### Permission Errors

Filesystem server only accesses the specified directory (`datasets/`).
If you get permission errors:

1. Check directory exists
2. Verify path is relative to project root
3. Check file permissions

### Server Timeout

If server takes too long to start:

1. Check internet connection (for npx downloads)
2. Increase timeout in settings
3. Try manual install:
   ```bash
   npm install -g @modelcontextprotocol/server-filesystem
   ```

## Documentation

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
- [Claude Code MCP Guide](https://docs.claude.com/en/docs/claude-code/mcp)

## Version

Created: 2025-11-16
Status: Filesystem server ready, GitHub server planned
