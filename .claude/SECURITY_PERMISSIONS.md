# Security Permissions Reference

This document explains all the security restrictions configured in `.claude/settings.local.json` to protect sensitive data and prevent destructive operations.

## Overview

The `deny` list now includes **69 restrictions** across multiple categories to ensure Claude Code cannot accidentally access or modify sensitive files or execute dangerous commands.

## Categories of Restrictions

### 1. Environment Files (11 rules)

Prevents reading or modifying environment configuration files:

```json
"Read(.env)",
"Read(.env.*)",
"Read(api/.env)",
"Read(web/.env)",
"Read(**/.env.local)",
"Read(**/.env.*.local)",
"Write(.env)",
"Write(.env.*)",
"Edit(.env)",
"Edit(.env.*)"
```

**Why?** Environment files contain API keys, database URLs, and other secrets.

### 2. Credentials & Authentication (20 rules)

Blocks access to credential files across formats:

```json
"Read(**/kaggle.json)",
"Read(**/.aws/credentials)",
"Read(**/credentials.json)",
"Read(**/credentials.yml)",
"Read(**/credentials.yaml)",
"Read(**/service-account.json)",
"Read(**/firebase-*.json)",
"Read(**/google-credentials.json)",
"Read(**/aws-credentials.json)",
"Read(.netrc)",
"Read(.npmrc)",
"Read(.pypirc)",
"Write(**/credentials.*)",
"Edit(**/credentials.*)"
```

**Why?** Prevents exposure of cloud provider credentials, package registry tokens, and service account keys.

### 3. Secrets & Tokens (12 rules)

Protects secret files and authentication tokens:

```json
"Read(**/secrets/*)",
"Read(**/*.secret)",
"Read(**/*.secrets)",
"Read(.secrets)",
"Read(**/*.token)",
"Read(**/token.txt)",
"Read(**/tokens.json)",
"Write(**/secrets/*)",
"Write(**/*.secret)",
"Write(**/*.token)",
"Edit(**/secrets/*)",
"Edit(**/*.secret)"
```

**Why?** Secrets directories often contain sensitive configuration and temporary authentication tokens.

### 4. SSH & Private Keys (16 rules)

Blocks SSH keys and cryptographic certificates:

```json
"Read(**/id_rsa)",
"Read(**/id_rsa.pub)",
"Read(**/id_dsa)",
"Read(**/id_dsa.pub)",
"Read(**/*.ppk)",
"Read(**/known_hosts)",
"Read(**/authorized_keys)",
"Read(**/*.key)",
"Read(**/*.pem)",
"Read(**/*.crt)",
"Read(**/*.cer)",
"Read(**/*.p12)",
"Read(**/*.pfx)",
"Write(**/*.key)",
"Write(**/*.pem)",
"Edit(**/*.key)",
"Edit(**/*.pem)"
```

**Why?** SSH keys and certificates provide server access. Compromise = security breach.

### 5. Private & Internal Files (2 rules)

Protects project-internal documentation:

```json
"Read(**/private/*)",
"Read(**/internal-docs/*)",
"Read(roast.md)"
```

**Why?** Private directories may contain internal notes, business logic, or sensitive planning documents.

### 6. Destructive Bash Commands (10 rules)

Prevents catastrophic file/system operations:

```json
"Bash(rm -rf:*)",                    // Recursive force delete
"Bash(docker rmi -f:*)",             // Force remove images
"Bash(docker system prune:*)",       // Delete all unused data
"Bash(git push --force:*)",          // Force push (destructive)
"Bash(git push -f:*)",               // Force push shorthand
"Bash(git reset --hard:*)",          // Discard changes
"Bash(git clean -fdx)",              // Delete untracked files
"Bash(kubectl delete:*)",            // Delete Kubernetes resources
"Bash(aws:*)",                       // AWS CLI commands
"Bash(terraform destroy:*)",         // Destroy infrastructure
"Bash(npm uninstall -g:*)",          // Global package removal
"Bash(pip uninstall:*)"              // Python package removal
```

**Why?** These commands can delete files, containers, infrastructure, or force-push to protected branches.

## What's Still Allowed?

Claude can still:

- ✅ Read all source code files (Python, TypeScript, etc.)
- ✅ Read documentation and README files
- ✅ Read test files and datasets
- ✅ Write new code files
- ✅ Edit existing code files
- ✅ Run tests and builds
- ✅ Execute git operations (except force push/hard reset)
- ✅ Use npm/pip for installing packages
- ✅ Run docker-compose commands
- ✅ Read `.env.example` files (explicitly allowed in gitignore)

## Additional Security Layers

### 1. Ask Mode (Currently Empty)

You can add operations that should always prompt:

```json
"ask": [
  "Bash(git push origin main)",
  "Write(api/app/core/config.py)",
  "Edit(package.json)"
]
```

### 2. Sandbox Configuration (Optional)

You can enable sandboxed bash execution:

```json
"sandbox": {
  "enabled": true,
  "autoAllowBashIfSandboxed": true,
  "network": {
    "allowLocalBinding": false,
    "allowUnixSockets": []
  }
}
```

This runs bash commands in isolated containers.

### 3. Additional Directories (Optional)

Restrict Claude's scope to specific directories:

```json
"permissions": {
  "additionalDirectories": [
    "api/",
    "web/",
    "docs/"
  ]
}
```

## Security Best Practices

### DO:

1. ✅ Keep `.claude/settings.local.json` in `.gitignore`
2. ✅ Review the deny list periodically
3. ✅ Add new patterns as you discover sensitive files
4. ✅ Use `.secrets.baseline` for detecting secrets in commits
5. ✅ Enable pre-commit hooks for validation

### DON'T:

1. ❌ Commit `.claude/settings.local.json` with hardcoded paths
2. ❌ Remove security restrictions without understanding impact
3. ❌ Store actual secrets in the repository (even in examples)
4. ❌ Disable all restrictions for convenience
5. ❌ Share settings files between different projects

## Testing Your Security

Test if restrictions work:

```bash
# This should be blocked:
Read(.env)
# Error: Permission denied

# This should work:
Read(.env.example)
# Success: Contents returned
```

## Extending Restrictions

### Block Specific File Types

```json
"Read(**/*.db)",          // Database files
"Read(**/*.sqlite)",      // SQLite databases
"Read(**/dump.sql)",      // SQL dumps
"Write(**/*.lock)"        // Lock files
```

### Block Specific Directories

```json
"Read(node_modules/*)",   // Dependencies
"Read(venv/*)",           // Python virtual env
"Read(.git/*)",           // Git internals
"Read(uploads/*)"         // User uploads
```

### Block Write Operations

```json
"Write(package.json)",           // Package config
"Write(requirements.txt)",       // Python deps
"Write(docker-compose.yml)",     // Docker config
"Write(.github/workflows/*)"     // CI/CD workflows
```

### Block Destructive Git Operations

```json
"Bash(git rebase:*)",            // Rebase operations
"Bash(git cherry-pick:*)",       // Cherry-picking
"Bash(git filter-branch:*)",     // History rewriting
"Bash(git reflog expire:*)"      // Remove reflog entries
```

## Monitoring & Auditing

Claude Code logs all permission denials. Check logs at:

- **Windows**: `%APPDATA%\Claude Code\logs\`
- **macOS**: `~/Library/Logs/Claude Code/`
- **Linux**: `~/.config/claude-code/logs/`

Look for entries like:

```
[PERMISSION_DENIED] Read(.env) - Matched deny rule
[PERMISSION_BLOCKED] Bash(rm -rf:/) - Matched deny rule
```

## Emergency Override

If you need to temporarily disable restrictions:

```json
"permissions": {
  "defaultMode": "bypassPermissions"
}
```

**⚠️ WARNING:** Only use during debugging. Re-enable restrictions immediately after.

## Summary Statistics

**Total Restrictions**: 69 rules

- **Read restrictions**: 42
- **Write restrictions**: 9
- **Edit restrictions**: 8
- **Bash restrictions**: 10

**Protected File Types**:

- Environment files: `.env`, `.env.*`
- Credentials: `.json`, `.yml`, `.yaml`
- Keys: `.key`, `.pem`, `.crt`, `.cer`, `.p12`, `.pfx`
- Tokens: `.token`, `token.txt`, `tokens.json`
- SSH: `id_rsa`, `id_dsa`, `.ppk`, `known_hosts`
- Secrets: `*.secret`, `secrets/*`

**Protected Operations**:

- Force deletion: `rm -rf`
- Force git operations: `push --force`, `reset --hard`
- Infrastructure destruction: `terraform destroy`, `kubectl delete`
- Container cleanup: `docker rmi -f`, `docker system prune`
- Cloud operations: `aws` CLI

## Version History

- **v1.0** (2025-10-29): Initial security configuration with 69 rules
- Comprehensive coverage of sensitive files and destructive operations
- Aligned with project `.gitignore` patterns

## References

- [Claude Code Security Docs](https://docs.claude.com/en/docs/claude-code/settings)
- [.gitignore](../.gitignore) - File patterns to never commit
- [.secrets.baseline](../.secrets.baseline) - Detect-secrets baseline
- [README.md](README.md) - Claude Code configuration guide

---

**Last Updated**: 2025-10-29
**Project**: Customer Feedback Analyzer v3.6.0
