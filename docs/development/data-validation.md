# Data Validation & Quality Checks

## Overview

Data quality is critical for the AI analyzer to produce accurate results. This document defines validation rules and quality checks.

## Input Validation

### Company Registration

```python
from pydantic import BaseModel, validator, HttpUrl
from typing import List, Optional
import re

class SocialAccountInput(BaseModel):
    platform: str
    identifier: str
    url: Optional[HttpUrl] = None

    @validator('platform')
    def validate_platform(cls, v):
        valid = ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']
        if v.lower() not in valid:
            raise ValueError(f'Invalid platform. Must be one of: {valid}')
        return v.lower()

    @validator('identifier')
    def validate_identifier(cls, v):
        # Remove @ prefix if present
        v = v.lstrip('@')

        # Check format
        if not re.match(r'^[a-zA-Z0-9._]+$', v):
            raise ValueError('Identifier must contain only letters, numbers, dots, and underscores')

        if len(v) < 1 or len(v) > 100:
            raise ValueError('Identifier must be 1-100 characters')

        return v

class CompanyInput(BaseModel):
    name: str
    industry: Optional[str] = None
    country: Optional[str] = None
    social_accounts: List[SocialAccountInput]

    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Company name must be at least 2 characters')
        if len(v) > 255:
            raise ValueError('Company name must be less than 255 characters')
        return v.strip()

    @validator('social_accounts')
    def validate_accounts(cls, v):
        if not v:
            raise ValueError('At least one social account is required')

        # Check for duplicate platforms
        platforms = [a.platform for a in v]
        if len(platforms) != len(set(platforms)):
            raise ValueError('Duplicate platforms not allowed')

        return v
```

### Extraction Request

```python
from datetime import date, datetime

class ExtractionOptions(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    max_posts_per_platform: int = 100
    max_comments_per_post: int = 500
    include_replies: bool = True

    @validator('date_from', 'date_to')
    def validate_dates(cls, v):
        if v and v > date.today():
            raise ValueError('Date cannot be in the future')
        return v

    @validator('date_to')
    def validate_date_range(cls, v, values):
        if v and values.get('date_from') and v < values['date_from']:
            raise ValueError('date_to must be after date_from')
        return v

    @validator('max_posts_per_platform')
    def validate_max_posts(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('max_posts_per_platform must be 1-1000')
        return v

    @validator('max_comments_per_post')
    def validate_max_comments(cls, v):
        if v < 1 or v > 10000:
            raise ValueError('max_comments_per_post must be 1-10000')
        return v
```

## Extracted Data Validation

### Comment Validation

```python
class CommentValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate(self, comment: dict) -> bool:
        """Validate a single comment. Returns True if valid."""
        self.errors = []
        self.warnings = []

        # Required fields
        self._check_required(comment, 'platform_id')
        self._check_required(comment, 'text')
        self._check_required(comment, 'platform')

        # Text validation
        self._validate_text(comment.get('text', ''))

        # Timestamp validation
        self._validate_timestamp(comment.get('published_at'))

        # Numeric fields
        self._validate_non_negative(comment.get('likes', 0), 'likes')
        self._validate_non_negative(comment.get('replies_count', 0), 'replies_count')

        # Author validation
        if comment.get('author'):
            self._validate_author(comment['author'])

        return len(self.errors) == 0

    def _check_required(self, data: dict, field: str):
        if not data.get(field):
            self.errors.append(f"Missing required field: {field}")

    def _validate_text(self, text: str):
        if not text or not text.strip():
            self.errors.append("Comment text is empty")
            return

        # Check for suspicious content
        if len(text) > 10000:
            self.warnings.append("Unusually long comment (>10000 chars)")

        # Check for encoding issues
        if '\x00' in text:
            self.warnings.append("Null characters in text")

    def _validate_timestamp(self, timestamp):
        if not timestamp:
            self.warnings.append("Missing timestamp")
            return

        if isinstance(timestamp, datetime):
            if timestamp > datetime.utcnow():
                self.errors.append("Timestamp is in the future")
        elif isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if dt > datetime.utcnow():
                    self.errors.append("Timestamp is in the future")
            except ValueError:
                self.errors.append(f"Invalid timestamp format: {timestamp}")

    def _validate_non_negative(self, value, field_name: str):
        if value is not None and value < 0:
            self.errors.append(f"{field_name} cannot be negative")

    def _validate_author(self, author: dict):
        if not author.get('platform_id') and not author.get('username'):
            self.warnings.append("Author missing both platform_id and username")
```

### Batch Validation

```python
class BatchValidator:
    def __init__(self):
        self.comment_validator = CommentValidator()
        self.stats = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'warnings': 0
        }

    def validate_batch(self, comments: list) -> dict:
        """Validate a batch of comments."""
        results = {
            'valid_comments': [],
            'invalid_comments': [],
            'errors': [],
            'warnings': []
        }

        for i, comment in enumerate(comments):
            self.stats['total'] += 1

            if self.comment_validator.validate(comment):
                self.stats['valid'] += 1
                results['valid_comments'].append(comment)
            else:
                self.stats['invalid'] += 1
                results['invalid_comments'].append({
                    'index': i,
                    'comment': comment,
                    'errors': self.comment_validator.errors
                })
                results['errors'].extend([
                    f"Comment {i}: {e}" for e in self.comment_validator.errors
                ])

            if self.comment_validator.warnings:
                self.stats['warnings'] += len(self.comment_validator.warnings)
                results['warnings'].extend([
                    f"Comment {i}: {w}" for w in self.comment_validator.warnings
                ])

        return results

    def get_stats(self) -> dict:
        return {
            **self.stats,
            'valid_rate': self.stats['valid'] / self.stats['total'] if self.stats['total'] > 0 else 0
        }
```

## Quality Checks

### Data Quality Metrics

```python
class DataQualityChecker:
    def __init__(self):
        self.metrics = {}

    def check_extraction(self, job_id: str, posts: list, comments: list) -> dict:
        """Run all quality checks on extracted data."""

        self.metrics = {
            'job_id': job_id,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }

        # Completeness checks
        self.metrics['checks']['completeness'] = self._check_completeness(posts, comments)

        # Consistency checks
        self.metrics['checks']['consistency'] = self._check_consistency(posts, comments)

        # Freshness checks
        self.metrics['checks']['freshness'] = self._check_freshness(posts, comments)

        # Uniqueness checks
        self.metrics['checks']['uniqueness'] = self._check_uniqueness(comments)

        # Overall score
        self.metrics['overall_score'] = self._calculate_score()

        return self.metrics

    def _check_completeness(self, posts: list, comments: list) -> dict:
        """Check for missing required fields."""
        results = {
            'posts_with_text': 0,
            'posts_with_timestamp': 0,
            'comments_with_author': 0,
            'comments_with_timestamp': 0
        }

        for post in posts:
            if post.get('text'):
                results['posts_with_text'] += 1
            if post.get('published_at'):
                results['posts_with_timestamp'] += 1

        for comment in comments:
            if comment.get('author_id') or comment.get('author', {}).get('username'):
                results['comments_with_author'] += 1
            if comment.get('published_at'):
                results['comments_with_timestamp'] += 1

        # Calculate percentages
        total_posts = len(posts) if posts else 1
        total_comments = len(comments) if comments else 1

        return {
            'post_text_rate': results['posts_with_text'] / total_posts,
            'post_timestamp_rate': results['posts_with_timestamp'] / total_posts,
            'comment_author_rate': results['comments_with_author'] / total_comments,
            'comment_timestamp_rate': results['comments_with_timestamp'] / total_comments,
            'passed': all([
                results['posts_with_timestamp'] / total_posts > 0.9,
                results['comments_with_author'] / total_comments > 0.8
            ])
        }

    def _check_consistency(self, posts: list, comments: list) -> dict:
        """Check data consistency."""
        issues = []

        # Check all comments reference valid posts
        post_ids = {p.get('id') or p.get('platform_id') for p in posts}
        orphan_comments = 0

        for comment in comments:
            if comment.get('post_id') not in post_ids:
                orphan_comments += 1

        if orphan_comments > 0:
            issues.append(f"{orphan_comments} comments reference non-existent posts")

        # Check comment counts match
        for post in posts:
            post_id = post.get('id') or post.get('platform_id')
            expected = post.get('comments_count', 0)
            actual = sum(1 for c in comments if c.get('post_id') == post_id)

            # Allow some variance (comments may be hidden/deleted)
            if actual < expected * 0.5 and expected > 10:
                issues.append(f"Post {post_id}: expected ~{expected} comments, got {actual}")

        return {
            'orphan_comments': orphan_comments,
            'issues': issues,
            'passed': orphan_comments == 0 and len(issues) <= len(posts) * 0.1
        }

    def _check_freshness(self, posts: list, comments: list) -> dict:
        """Check data freshness."""
        now = datetime.utcnow()
        oldest_post = None
        newest_post = None

        for post in posts:
            ts = post.get('published_at')
            if ts:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                if oldest_post is None or ts < oldest_post:
                    oldest_post = ts
                if newest_post is None or ts > newest_post:
                    newest_post = ts

        return {
            'oldest_post': oldest_post.isoformat() if oldest_post else None,
            'newest_post': newest_post.isoformat() if newest_post else None,
            'data_age_hours': (now - newest_post).total_seconds() / 3600 if newest_post else None,
            'passed': newest_post and (now - newest_post).days < 7
        }

    def _check_uniqueness(self, comments: list) -> dict:
        """Check for duplicates."""
        seen_ids = set()
        duplicates = 0

        for comment in comments:
            comment_id = f"{comment.get('platform')}:{comment.get('platform_id')}"
            if comment_id in seen_ids:
                duplicates += 1
            seen_ids.add(comment_id)

        return {
            'total_comments': len(comments),
            'unique_comments': len(seen_ids),
            'duplicates': duplicates,
            'duplicate_rate': duplicates / len(comments) if comments else 0,
            'passed': duplicates == 0
        }

    def _calculate_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        checks = self.metrics['checks']

        scores = []

        if checks['completeness']['passed']:
            scores.append(25)
        else:
            scores.append(checks['completeness']['comment_author_rate'] * 25)

        if checks['consistency']['passed']:
            scores.append(25)
        else:
            scores.append(max(0, 25 - len(checks['consistency']['issues']) * 2))

        if checks['freshness']['passed']:
            scores.append(25)
        else:
            scores.append(0)

        if checks['uniqueness']['passed']:
            scores.append(25)
        else:
            scores.append(25 * (1 - checks['uniqueness']['duplicate_rate']))

        return round(sum(scores), 2)
```

### Quality Gates

```python
class QualityGate:
    """
    Enforce quality standards before data is accepted.
    """

    def __init__(self):
        self.thresholds = {
            'min_valid_rate': 0.95,      # 95% of comments must be valid
            'max_duplicate_rate': 0.01,   # Max 1% duplicates
            'min_author_rate': 0.80,      # 80% must have author info
            'min_quality_score': 70       # Overall score >= 70
        }

    def check(self, validation_results: dict, quality_metrics: dict) -> tuple[bool, list]:
        """
        Check if data passes quality gates.
        Returns (passed, list_of_failures)
        """
        failures = []

        # Validation rate
        valid_rate = validation_results['stats']['valid_rate']
        if valid_rate < self.thresholds['min_valid_rate']:
            failures.append(
                f"Valid rate {valid_rate:.2%} below threshold {self.thresholds['min_valid_rate']:.2%}"
            )

        # Duplicate rate
        dup_rate = quality_metrics['checks']['uniqueness']['duplicate_rate']
        if dup_rate > self.thresholds['max_duplicate_rate']:
            failures.append(
                f"Duplicate rate {dup_rate:.2%} above threshold {self.thresholds['max_duplicate_rate']:.2%}"
            )

        # Author rate
        author_rate = quality_metrics['checks']['completeness']['comment_author_rate']
        if author_rate < self.thresholds['min_author_rate']:
            failures.append(
                f"Author rate {author_rate:.2%} below threshold {self.thresholds['min_author_rate']:.2%}"
            )

        # Overall score
        score = quality_metrics['overall_score']
        if score < self.thresholds['min_quality_score']:
            failures.append(
                f"Quality score {score} below threshold {self.thresholds['min_quality_score']}"
            )

        return len(failures) == 0, failures
```

## Data Cleansing

### Text Cleansing

```python
import re
import unicodedata

class TextCleaner:
    def clean(self, text: str) -> str:
        if not text:
            return ""

        # Normalize unicode
        text = unicodedata.normalize('NFKC', text)

        # Remove null characters
        text = text.replace('\x00', '')

        # Normalize whitespace
        text = ' '.join(text.split())

        # Remove control characters (except newlines)
        text = ''.join(
            char for char in text
            if not unicodedata.category(char).startswith('C')
            or char in '\n\r\t'
        )

        return text.strip()

    def extract_metadata(self, text: str) -> dict:
        """Extract metadata from text."""
        return {
            'mentions': re.findall(r'@(\w+)', text),
            'hashtags': re.findall(r'#(\w+)', text),
            'urls': re.findall(r'https?://\S+', text),
            'emojis': self._extract_emojis(text)
        }

    def _extract_emojis(self, text: str) -> list:
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # Emoticons
            "\U0001F300-\U0001F5FF"   # Symbols & pictographs
            "\U0001F680-\U0001F6FF"   # Transport & map
            "\U0001F1E0-\U0001F1FF"   # Flags
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.findall(text)
```

## Quality Reports

### Generate Quality Report

```python
class QualityReporter:
    def generate_report(
        self,
        job_id: str,
        validation_results: dict,
        quality_metrics: dict
    ) -> dict:
        """Generate comprehensive quality report."""

        gate = QualityGate()
        passed, failures = gate.check(validation_results, quality_metrics)

        return {
            'job_id': job_id,
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'passed': passed,
                'quality_score': quality_metrics['overall_score'],
                'total_items': validation_results['stats']['total'],
                'valid_items': validation_results['stats']['valid'],
                'invalid_items': validation_results['stats']['invalid']
            },
            'validation': {
                'valid_rate': validation_results['stats']['valid_rate'],
                'errors': validation_results['errors'][:100],  # Limit
                'warnings': validation_results['warnings'][:100]
            },
            'quality_checks': quality_metrics['checks'],
            'gate_failures': failures,
            'recommendations': self._generate_recommendations(
                validation_results, quality_metrics
            )
        }

    def _generate_recommendations(
        self,
        validation_results: dict,
        quality_metrics: dict
    ) -> list:
        """Generate actionable recommendations."""
        recommendations = []

        # Check for common issues
        if validation_results['stats']['valid_rate'] < 0.95:
            recommendations.append(
                "Review extractor for common validation errors"
            )

        if quality_metrics['checks']['uniqueness']['duplicate_rate'] > 0.01:
            recommendations.append(
                "Check deduplication logic in extractor"
            )

        if quality_metrics['checks']['completeness']['comment_author_rate'] < 0.8:
            recommendations.append(
                "Author information incomplete - may affect commenter analysis"
            )

        return recommendations
```
