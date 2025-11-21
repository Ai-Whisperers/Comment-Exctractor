# Database Schema Designer Skill

Design and validate database schemas for SQLAlchemy models with best practices.

## Metadata

- Name: Database Schema Designer
- Category: Database & Architecture
- Activation: Automatic when database schema design mentioned
- Model: Sonnet (complex design decisions)
- Token Cost: ~1,200 tokens

## When to Activate

Trigger this skill when user mentions:
- "Design database schema"
- "Create database model"
- "Add new table"
- "Database migration"
- "SQLAlchemy model"
- "Foreign key relationship"
- "Database normalization"

## Core Capabilities

### 1. SQLAlchemy Model Generation

Generate production-ready SQLAlchemy models with:
- Proper type hints
- Relationship definitions
- Indexes for performance
- Constraints (unique, check, foreign key)
- Default values
- Timestamps (created_at, updated_at)

### 2. Alembic Migration Creation

Automatically generate:
- Upgrade scripts (create tables, add columns)
- Downgrade scripts (rollback changes)
- Data migration logic when needed
- Index creation/removal
- Constraint modifications

### 3. Relationship Validation

Check for:
- Circular dependencies
- Missing foreign key indexes
- Orphaned records (cascade delete issues)
- N+1 query problems
- Proper back_populates definitions

### 4. Performance Analysis

Suggest:
- Composite indexes for common queries
- Partial indexes for filtered queries
- Covering indexes for read-heavy tables
- Database denormalization opportunities
- Materialized views for complex aggregations

### 5. Normalization Checking

Validate:
- 1NF, 2NF, 3NF compliance
- Identify transitive dependencies
- Suggest table splitting for better organization
- Check for repeating groups

## Project-Specific Context

### Current Database Setup

```python
# Customer Feedback Analyzer uses:
Database: PostgreSQL (production) / SQLite (development)
ORM: SQLAlchemy
Migration Tool: Alembic
Connection Pool: 20 connections max
```

### Existing Tables

1. feedback_analysis
   - id (primary key)
   - customer_id
   - comment_text
   - user_score
   - sentiment_score
   - churn_risk
   - created_at

2. analysis_cache
   - id (primary key)
   - comment_hash (SHA256)
   - cached_result (JSON)
   - created_at
   - expires_at

### Design Patterns Used

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Usage Examples

### Example 1: Pain Point Tracking Table

```
User: Design database schema for pain point tracking

Skill generates:

1. SQLAlchemy Model (api/app/domain/models/pain_point.py):

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.domain.models.base import BaseModel

class PainPoint(BaseModel):
    __tablename__ = 'pain_points'

    # Primary fields
    feedback_id = Column(Integer, ForeignKey('feedback_analysis.id'), nullable=False)
    category = Column(String(50), nullable=False)  # CONNECTIVITY, SPEED, etc.
    subcategory = Column(String(50), nullable=True)
    keywords = Column(String(500), nullable=True)
    severity = Column(Integer, nullable=False)  # 1-10

    # Relationships
    feedback = relationship("FeedbackAnalysis", back_populates="pain_points")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_pain_category', 'category'),
        Index('idx_pain_severity', 'severity'),
        Index('idx_pain_feedback_category', 'feedback_id', 'category'),
    )

2. Alembic Migration (api/alembic/versions/xxx_add_pain_points.py):

def upgrade():
    op.create_table(
        'pain_points',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feedback_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('subcategory', sa.String(50), nullable=True),
        sa.Column('keywords', sa.String(500), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['feedback_id'], ['feedback_analysis.id']),
    )

    op.create_index('idx_pain_category', 'pain_points', ['category'])
    op.create_index('idx_pain_severity', 'pain_points', ['severity'])
    op.create_index('idx_pain_feedback_category', 'pain_points', ['feedback_id', 'category'])

def downgrade():
    op.drop_index('idx_pain_feedback_category', table_name='pain_points')
    op.drop_index('idx_pain_severity', table_name='pain_points')
    op.drop_index('idx_pain_category', table_name='pain_points')
    op.drop_table('pain_points')

3. Performance Recommendations:

- Composite index on (feedback_id, category) for filtered queries
- Severity index for priority-based filtering
- Consider partial index: WHERE severity >= 7 (high priority only)
- Add CHECK constraint: severity BETWEEN 1 AND 10
```

### Example 2: Customer Timeline Table

```
User: Add table to track customer feedback timeline

Skill generates:

1. Model with proper relationships:

class CustomerTimeline(BaseModel):
    __tablename__ = 'customer_timeline'

    customer_id = Column(String(100), nullable=False)
    feedback_id = Column(Integer, ForeignKey('feedback_analysis.id'))
    event_type = Column(String(50), nullable=False)  # FEEDBACK, ESCALATION, RESOLVED
    event_data = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=False)

    # Relationships
    feedback = relationship("FeedbackAnalysis")

    # Indexes
    __table_args__ = (
        Index('idx_customer_timeline', 'customer_id', 'occurred_at'),
        Index('idx_timeline_event_type', 'event_type'),
    )

2. N+1 Query Prevention:

# Bad (N+1 problem)
timelines = session.query(CustomerTimeline).all()
for timeline in timelines:
    print(timeline.feedback.comment_text)  # Extra query per row!

# Good (eager loading)
from sqlalchemy.orm import joinedload

timelines = session.query(CustomerTimeline)\
    .options(joinedload(CustomerTimeline.feedback))\
    .all()

3. Migration with data migration:

def upgrade():
    # Create table
    op.create_table('customer_timeline', ...)

    # Migrate existing data
    connection = op.get_bind()
    connection.execute('''
        INSERT INTO customer_timeline (customer_id, feedback_id, event_type, occurred_at)
        SELECT customer_id, id, 'FEEDBACK', created_at
        FROM feedback_analysis
    ''')

def downgrade():
    op.drop_table('customer_timeline')
```

## Best Practices Enforced

### 1. Always Add Indexes

```python
# Common query patterns should have indexes
__table_args__ = (
    Index('idx_customer_id', 'customer_id'),  # Single column
    Index('idx_customer_date', 'customer_id', 'created_at'),  # Composite
    Index('idx_high_churn', 'churn_risk', postgresql_where=text('churn_risk > 70')),  # Partial
)
```

### 2. Use Proper Constraints

```python
from sqlalchemy import CheckConstraint

class Review(BaseModel):
    user_score = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint('user_score >= 0 AND user_score <= 10', name='valid_score'),
    )
```

### 3. Avoid Nullable Foreign Keys (Unless Intentional)

```python
# Bad (orphaned records possible)
feedback_id = Column(Integer, ForeignKey('feedback_analysis.id'), nullable=True)

# Good (enforced relationship)
feedback_id = Column(Integer, ForeignKey('feedback_analysis.id'), nullable=False)
```

### 4. Use Enums for Fixed Values

```python
from enum import Enum as PyEnum
from sqlalchemy import Enum

class PainPointCategory(PyEnum):
    CONNECTIVITY = "CONNECTIVITY"
    SPEED = "SPEED"
    SUPPORT = "SUPPORT"
    BILLING = "BILLING"

class PainPoint(BaseModel):
    category = Column(Enum(PainPointCategory), nullable=False)
```

### 5. Add Cascade Delete Rules

```python
class PainPoint(BaseModel):
    feedback_id = Column(
        Integer,
        ForeignKey('feedback_analysis.id', ondelete='CASCADE'),
        nullable=False
    )

    feedback = relationship(
        "FeedbackAnalysis",
        back_populates="pain_points",
        cascade="all, delete-orphan"
    )
```

## Validation Checklist

Before finalizing schema design, verify:

- [ ] All foreign keys have indexes
- [ ] Composite indexes for common multi-column queries
- [ ] Proper nullable constraints (nullable=False where required)
- [ ] Check constraints for data validation
- [ ] Unique constraints for natural keys
- [ ] Cascade delete rules defined
- [ ] back_populates on both sides of relationships
- [ ] created_at and updated_at timestamps
- [ ] Enum types for fixed value sets
- [ ] Migration has both upgrade and downgrade
- [ ] Data migration logic if needed
- [ ] Index naming follows convention (idx_table_column)

## Performance Guidelines

### Index Strategy

```python
# Single column (common filters)
Index('idx_category', 'category')

# Composite (multi-column queries)
Index('idx_customer_date', 'customer_id', 'created_at')

# Partial (filtered queries)
Index('idx_high_priority', 'priority_score',
      postgresql_where=text('priority_score >= 60'))

# Covering (avoid table lookup)
Index('idx_customer_cover', 'customer_id', 'user_score', 'churn_risk')
```

### Query Optimization

```python
# Use select_related for single relationships
feedback = session.query(FeedbackAnalysis)\
    .options(joinedload(FeedbackAnalysis.pain_points))\
    .filter_by(id=123)\
    .first()

# Use subqueries for aggregations
from sqlalchemy import func

high_churn_count = session.query(
    func.count(FeedbackAnalysis.id)
).filter(
    FeedbackAnalysis.churn_risk > 70
).scalar()
```

## Common Patterns

### 1. Soft Delete

```python
class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

# Query only non-deleted
session.query(FeedbackAnalysis)\
    .filter(FeedbackAnalysis.deleted_at.is_(None))\
    .all()
```

### 2. Audit Trail

```python
class AuditMixin:
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

### 3. Versioning

```python
class VersionedMixin:
    version = Column(Integer, default=1, nullable=False)

    __mapper_args__ = {
        "version_id_col": version
    }
```

## Migration Safety

### Safe Operations (No Downtime)

- Add nullable column
- Add index (with CONCURRENTLY on PostgreSQL)
- Add table (if not referenced yet)
- Drop index
- Increase column size

### Unsafe Operations (Require Downtime)

- Drop column (data loss)
- Rename column (breaks existing code)
- Add NOT NULL column to existing table
- Change column type
- Add foreign key to large table

### Multi-Step Migration Strategy

```python
# Step 1: Add nullable column
def upgrade():
    op.add_column('feedback_analysis', sa.Column('new_field', sa.String(100)))

# Step 2: Backfill data (separate migration)
def upgrade():
    connection = op.get_bind()
    connection.execute("UPDATE feedback_analysis SET new_field = 'default'")

# Step 3: Make NOT NULL (separate migration)
def upgrade():
    op.alter_column('feedback_analysis', 'new_field', nullable=False)
```

## Testing Strategy

```python
# api/tests/models/test_pain_point.py

import pytest
from sqlalchemy.exc import IntegrityError
from app.domain.models import PainPoint, FeedbackAnalysis

def test_pain_point_requires_feedback(db_session):
    pain_point = PainPoint(category="CONNECTIVITY", severity=8)

    with pytest.raises(IntegrityError):
        db_session.add(pain_point)
        db_session.commit()  # Should fail - no feedback_id

def test_pain_point_cascade_delete(db_session):
    feedback = FeedbackAnalysis(comment_text="Test", user_score=5)
    pain_point = PainPoint(feedback=feedback, category="SPEED", severity=7)

    db_session.add_all([feedback, pain_point])
    db_session.commit()

    db_session.delete(feedback)
    db_session.commit()

    # Pain point should be deleted automatically
    assert db_session.query(PainPoint).count() == 0

def test_index_exists(db_session):
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    indexes = inspector.get_indexes('pain_points')

    index_names = [idx['name'] for idx in indexes]
    assert 'idx_pain_category' in index_names
```

## Quick Reference

```bash
# Generate migration
cd api
alembic revision --autogenerate -m "Add pain points table"

# Review migration (ALWAYS check before applying)
cat alembic/versions/xxx_add_pain_points.py

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current version
alembic current

# View migration history
alembic history
```

## Success Criteria

Schema design is complete when:

- [ ] SQLAlchemy models generated with type hints
- [ ] Alembic migration created (upgrade + downgrade)
- [ ] All foreign keys indexed
- [ ] Common query patterns have composite indexes
- [ ] Relationships properly defined (back_populates)
- [ ] Constraints added (CHECK, UNIQUE, NOT NULL)
- [ ] Cascade delete rules specified
- [ ] Migration tested on development database
- [ ] Tests written for model constraints
- [ ] Documentation updated

## Related Files

- [CLAUDE.md](../../../CLAUDE.md) - Database conventions
- [api/app/domain/models/](../../../api/app/domain/models/) - Existing models
- [api/alembic/](../../../api/alembic/) - Migration files
- [api/tests/models/](../../../api/tests/models/) - Model tests

## Version

Last Updated: 2025-11-16
Status: Ready for use
