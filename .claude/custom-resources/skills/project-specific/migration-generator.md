# Migration Generator Skill

Generate safe database migrations with Alembic for SQLAlchemy models.

## Metadata

- Name: Migration Generator
- Category: Database & DevOps
- Activation: Automatic when migration mentioned
- Model: Haiku (fast generation)
- Token Cost: ~600 tokens

## When to Activate

Trigger this skill when user mentions:
- "Generate migration"
- "Create migration"
- "Alembic migration"
- "Database migration"
- "Add column"
- "Modify schema"

## Core Capabilities

### 1. Detect Model Changes

Automatically detect:
- New tables added
- Columns added/removed
- Column types changed
- Constraints added/removed
- Indexes added/removed

### 2. Generate Safe Migrations

Create migrations with:
- Upgrade script
- Downgrade script (rollback)
- Data migration logic
- Safety checks

### 3. Validate Migration Safety

Check for:
- Data loss risks
- Breaking changes
- Performance impact
- Locking issues

## Project-Specific Context

### Alembic Setup

```python
# Location: api/alembic/
# Config: api/alembic.ini
# Versions: api/alembic/versions/

# Database: PostgreSQL (production), SQLite (dev)
# Naming convention: {revision}_{description}.py
```

### Current Models

- FeedbackAnalysis
- AnalysisCache
- PainPoint (if added via database-schema-designer)

## Usage Examples

### Example 1: Add Column to Existing Table

```
User: Generate migration to add Review_Priority_Score column

Skill generates:

1. Auto-detect changes:

cd api
alembic revision --autogenerate -m "Add Review_Priority_Score column"

2. Review generated migration (api/alembic/versions/xxx_add_review_priority_score.py):

"""Add Review_Priority_Score column

Revision ID: abc123def456
Revises: prev_revision
Create Date: 2025-11-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123def456'
down_revision = 'prev_revision'
branch_labels = None
depends_on = None

def upgrade():
    # Add column as nullable first (safe)
    op.add_column(
        'feedback_analysis',
        sa.Column('Review_Priority_Score', sa.Integer(), nullable=True)
    )

def downgrade():
    op.drop_column('feedback_analysis', 'Review_Priority_Score')

3. Safety Analysis:

SAFE OPERATIONS:
- Adding nullable column: YES (no downtime)
- Column type Integer: YES (simple type)

WARNINGS:
- Column is nullable but should have default value
- Consider backfilling data before making NOT NULL

4. Improved Migration (multi-step):

# Step 1: Add nullable column
def upgrade():
    op.add_column(
        'feedback_analysis',
        sa.Column('Review_Priority_Score', sa.Integer(), nullable=True)
    )

# Step 2: Backfill data (separate migration)
def upgrade():
    connection = op.get_bind()
    connection.execute(
        '''
        UPDATE feedback_analysis
        SET Review_Priority_Score = CASE
            WHEN churn_risk >= 80 THEN 80
            WHEN churn_risk >= 60 THEN 60
            WHEN churn_risk >= 40 THEN 40
            ELSE 20
        END
        WHERE Review_Priority_Score IS NULL
        '''
    )

# Step 3: Make NOT NULL (separate migration)
def upgrade():
    op.alter_column(
        'feedback_analysis',
        'Review_Priority_Score',
        nullable=False,
        server_default='0'
    )
```

### Example 2: Add New Table with Relationships

```
User: Generate migration for pain_points table

Skill generates:

"""Add pain_points table

Revision ID: def456ghi789
Revises: abc123def456
Create Date: 2025-11-16 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'def456ghi789'
down_revision = 'abc123def456'
branch_labels = None
depends_on = None

def upgrade():
    # Create table
    op.create_table(
        'pain_points',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feedback_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subcategory', sa.String(length=50), nullable=True),
        sa.Column('keywords', sa.String(length=500), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['feedback_id'],
            ['feedback_analysis.id'],
            name='fk_pain_points_feedback_id',
            ondelete='CASCADE'
        ),
        sa.CheckConstraint(
            'severity >= 1 AND severity <= 10',
            name='ck_pain_points_severity_range'
        )
    )

    # Create indexes
    op.create_index('idx_pain_category', 'pain_points', ['category'])
    op.create_index('idx_pain_severity', 'pain_points', ['severity'])
    op.create_index(
        'idx_pain_feedback_category',
        'pain_points',
        ['feedback_id', 'category']
    )

def downgrade():
    # Drop indexes first
    op.drop_index('idx_pain_feedback_category', table_name='pain_points')
    op.drop_index('idx_pain_severity', table_name='pain_points')
    op.drop_index('idx_pain_category', table_name='pain_points')

    # Drop table
    op.drop_table('pain_points')

Safety Analysis:

SAFE:
- Creating new table: YES (no impact on existing data)
- Adding indexes: YES (table is empty)
- Foreign key with CASCADE: YES (safe delete behavior)

BEST PRACTICES APPLIED:
- Constraint names specified (easier debugging)
- Indexes created for common queries
- Check constraint for data validation
- Proper downgrade script
```

### Example 3: Change Column Type (Unsafe)

```
User: Generate migration to change user_score from Integer to Float

Skill generates:

"""Change user_score to Float

DANGER: This migration requires downtime and careful planning

Revision ID: ghi789jkl012
Revises: def456ghi789

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # UNSAFE: Direct column type change
    # This will lock the table during conversion

    # Safer approach: Multi-step migration

    # Step 1: Add new column
    op.add_column(
        'feedback_analysis',
        sa.Column('user_score_new', sa.Float(), nullable=True)
    )

    # Step 2: Copy data
    connection = op.get_bind()
    connection.execute(
        '''
        UPDATE feedback_analysis
        SET user_score_new = CAST(user_score AS FLOAT)
        '''
    )

    # Step 3: Make NOT NULL (after backfill)
    op.alter_column(
        'feedback_analysis',
        'user_score_new',
        nullable=False
    )

    # Step 4: Rename columns (requires app downtime)
    op.alter_column('feedback_analysis', 'user_score', new_column_name='user_score_old')
    op.alter_column('feedback_analysis', 'user_score_new', new_column_name='user_score')

    # Step 5: Drop old column (after verification)
    # op.drop_column('feedback_analysis', 'user_score_old')

def downgrade():
    # Add old column back
    op.add_column(
        'feedback_analysis',
        sa.Column('user_score_old', sa.Integer(), nullable=True)
    )

    # Copy data back (with precision loss!)
    connection = op.get_bind()
    connection.execute(
        '''
        UPDATE feedback_analysis
        SET user_score_old = CAST(user_score AS INTEGER)
        '''
    )

    # Rename
    op.alter_column('feedback_analysis', 'user_score', new_column_name='user_score_float')
    op.alter_column('feedback_analysis', 'user_score_old', new_column_name='user_score')

    # Drop float column
    op.drop_column('feedback_analysis', 'user_score_float')

WARNINGS:
- Type change: UNSAFE (requires downtime)
- Data conversion: LOSSY (precision lost in downgrade)
- Table locking: HIGH (large table risk)

RECOMMENDATION:
Split into 5 separate migrations:
1. Add user_score_new column (nullable)
2. Backfill user_score_new from user_score
3. Make user_score_new NOT NULL
4. Deploy code to use user_score_new
5. Drop user_score_old after verification
```

## Migration Safety Rules

### Safe Operations (No Downtime)

```python
# Add nullable column
op.add_column('table', sa.Column('new_col', sa.String(), nullable=True))

# Add index (PostgreSQL CONCURRENTLY)
op.create_index('idx_name', 'table', ['column'], postgresql_concurrently=True)

# Add table (if not referenced)
op.create_table('new_table', ...)

# Drop index
op.drop_index('idx_name')

# Increase column size
op.alter_column('table', 'column', type_=sa.String(200))  # was 100
```

### Unsafe Operations (Require Planning)

```python
# Drop column (data loss)
op.drop_column('table', 'column')

# Rename column (breaks old code)
op.alter_column('table', 'old_name', new_column_name='new_name')

# Add NOT NULL constraint (fails if nulls exist)
op.alter_column('table', 'column', nullable=False)

# Change column type (type conversion)
op.alter_column('table', 'column', type_=sa.Float())

# Add foreign key to large table (locks table)
op.create_foreign_key('fk_name', 'table', 'ref_table', ['col'], ['ref_col'])
```

## Best Practices

### 1. Always Review Generated Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# IMPORTANT: Review the file before applying
cat alembic/versions/xxx_description.py

# Check for:
# - Unexpected changes
# - Missing downgrade logic
# - Data loss risks
```

### 2. Test Migrations Locally

```bash
# Apply migration
alembic upgrade head

# Verify data
psql -d dev_db -c "SELECT * FROM table LIMIT 5;"

# Test rollback
alembic downgrade -1

# Verify rollback worked
psql -d dev_db -c "SELECT * FROM table LIMIT 5;"
```

### 3. Use Naming Conventions

```python
# alembic/env.py
from sqlalchemy import MetaData

metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})
```

### 4. Add Data Migrations

```python
def upgrade():
    # Schema change
    op.add_column('feedback_analysis', sa.Column('new_field', sa.String()))

    # Data migration
    connection = op.get_bind()
    connection.execute(
        '''
        UPDATE feedback_analysis
        SET new_field = 'default_value'
        WHERE new_field IS NULL
        '''
    )
```

### 5. Handle Production Carefully

```python
# For large tables, add timeouts
def upgrade():
    connection = op.get_bind()

    # Set statement timeout (30 seconds)
    connection.execute('SET statement_timeout = 30000')

    # Your migration
    op.add_column(...)

    # Reset timeout
    connection.execute('SET statement_timeout = 0')
```

## Quick Reference

```bash
# Generate migration
cd api
alembic revision --autogenerate -m "Description"

# Review migration
cat alembic/versions/xxx_description.py

# Check current version
alembic current

# View pending migrations
alembic heads

# Apply migration
alembic upgrade head

# Apply specific migration
alembic upgrade +1

# Rollback migration
alembic downgrade -1

# View history
alembic history

# Generate SQL (don't execute)
alembic upgrade head --sql

# Stamp database (mark as migrated without running)
alembic stamp head
```

## Migration Checklist

Before applying migration:

- [ ] Migration reviewed manually
- [ ] Downgrade script tested
- [ ] Data loss risks assessed
- [ ] Backup created
- [ ] Applied to dev/staging first
- [ ] Rollback plan documented
- [ ] Team notified (if downtime)
- [ ] Monitoring ready

## Common Issues

### Issue 1: Autogenerate Misses Changes

```python
# Problem: Alembic doesn't detect all changes

# Solution: Compare detection
alembic revision --autogenerate -m "Test"
# Then manually add missing changes

# Common missed changes:
# - Check constraints
# - Enum types
# - Indexes on expressions
# - Server defaults
```

### Issue 2: Circular Dependencies

```python
# Problem: Migration depends on future migration

# Solution: Use depends_on
revision = 'current'
down_revision = 'prev'
depends_on = 'other_branch'  # Wait for this
```

### Issue 3: Production Timeout

```python
# Problem: Large table migration times out

# Solution: Batch processing
def upgrade():
    connection = op.get_bind()

    # Process in batches
    batch_size = 1000
    offset = 0

    while True:
        result = connection.execute(f'''
            UPDATE feedback_analysis
            SET new_field = calculated_value
            WHERE id IN (
                SELECT id FROM feedback_analysis
                WHERE new_field IS NULL
                LIMIT {batch_size}
                OFFSET {offset}
            )
        ''')

        if result.rowcount == 0:
            break

        offset += batch_size
```

## Testing Strategy

```python
# api/tests/migrations/test_migrations.py

import pytest
from alembic import command
from alembic.config import Config

def test_upgrade_downgrade():
    # Get Alembic config
    config = Config("alembic.ini")

    # Upgrade
    command.upgrade(config, "head")

    # Verify schema
    # (check tables, columns, etc.)

    # Downgrade
    command.downgrade(config, "-1")

    # Verify rollback worked
```

## Success Criteria

Migration is ready when:

- [ ] Generated with alembic revision
- [ ] Reviewed manually
- [ ] Downgrade script complete
- [ ] Safety assessment done
- [ ] Data migration included (if needed)
- [ ] Tested locally (up and down)
- [ ] Documentation updated
- [ ] Team reviewed (for production)

## Related Skills

- [database-schema-designer.md](database-schema-designer.md) - Schema design
- [CLAUDE.md](../../../CLAUDE.md) - Migration conventions

## Version

Last Updated: 2025-11-16
Status: Ready for use
