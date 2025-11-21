# Testing Strategy

## Testing Pyramid

```
        /\
       /  \     E2E Tests (5%)
      /----\    - Full extraction flows
     /      \
    /--------\  Integration Tests (25%)
   /          \ - Database operations
  /            \- API endpoints
 /--------------\ - External service mocks
/                \
/==================\ Unit Tests (70%)
                    - Extractors
                    - Normalizers
                    - Validators
```

## Test Structure

```
tests/
├── unit/
│   ├── test_extractors/
│   │   ├── test_facebook.py
│   │   ├── test_instagram.py
│   │   ├── test_twitter.py
│   │   └── test_normalizer.py
│   ├── test_models/
│   │   ├── test_comment.py
│   │   └── test_validation.py
│   └── test_utils/
│       ├── test_retry.py
│       └── test_rate_limiter.py
├── integration/
│   ├── test_api/
│   │   ├── test_companies.py
│   │   ├── test_extractions.py
│   │   └── test_exports.py
│   ├── test_database/
│   │   └── test_repositories.py
│   └── test_workers/
│       └── test_extraction_task.py
├── e2e/
│   └── test_full_extraction.py
├── fixtures/
│   ├── facebook_responses.json
│   ├── instagram_responses.json
│   └── sample_comments.json
└── conftest.py
```

## Unit Tests

### Extractor Tests

```python
# tests/unit/test_extractors/test_facebook.py

import pytest
from unittest.mock import AsyncMock, patch
from src.extractors.facebook import FacebookExtractor

class TestFacebookExtractor:
    @pytest.fixture
    def extractor(self):
        return FacebookExtractor({"apify_api_key": "test_key"})

    @pytest.fixture
    def mock_apify_response(self):
        return {
            "defaultDatasetId": "dataset123",
            "items": [
                {
                    "postId": "123456789",
                    "text": "Test post content",
                    "time": "2024-01-15T10:30:00Z",
                    "likes": 100,
                    "comments": 25,
                    "shares": 10
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_get_posts_success(self, extractor, mock_apify_response):
        with patch.object(extractor.client.actor, 'call') as mock_call:
            mock_call.return_value = {"defaultDatasetId": "dataset123"}

            with patch.object(
                extractor.client.dataset, 'iterate_items'
            ) as mock_items:
                mock_items.return_value = iter(mock_apify_response["items"])

                posts = list(extractor.get_posts("personalpy", {}))

                assert len(posts) == 1
                assert posts[0]["platform_id"] == "123456789"
                assert posts[0]["likes"] == 100

    @pytest.mark.asyncio
    async def test_get_posts_empty(self, extractor):
        with patch.object(extractor.client.actor, 'call') as mock_call:
            mock_call.return_value = {"defaultDatasetId": "dataset123"}

            with patch.object(
                extractor.client.dataset, 'iterate_items'
            ) as mock_items:
                mock_items.return_value = iter([])

                posts = list(extractor.get_posts("personalpy", {}))
                assert len(posts) == 0

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, extractor):
        with patch.object(extractor.client.actor, 'call') as mock_call:
            mock_call.side_effect = Exception("Rate limit exceeded")

            with pytest.raises(Exception) as exc_info:
                list(extractor.get_posts("personalpy", {}))

            assert "Rate limit" in str(exc_info.value)


class TestFacebookNormalizer:
    def test_normalize_post(self):
        from src.extractors.facebook import FacebookExtractor

        raw_post = {
            "postId": "123",
            "text": "Hello world",
            "time": "2024-01-15T10:30:00Z",
            "likes": 50,
            "comments": 10,
            "shares": 5
        }

        normalized = FacebookExtractor._normalize_post(raw_post)

        assert normalized["platform_id"] == "123"
        assert normalized["text"] == "Hello world"
        assert normalized["likes"] == 50

    def test_normalize_post_missing_fields(self):
        raw_post = {
            "postId": "123",
            "text": None
        }

        normalized = FacebookExtractor._normalize_post(raw_post)

        assert normalized["text"] == ""
        assert normalized["likes"] == 0
```

### Normalizer Tests

```python
# tests/unit/test_extractors/test_normalizer.py

import pytest
from datetime import datetime
from src.extractors.normalizer import DataNormalizer

class TestDataNormalizer:
    @pytest.fixture
    def normalizer(self):
        return DataNormalizer()

    def test_clean_text_whitespace(self, normalizer):
        text = "  hello   world  \n\n test  "
        result = normalizer._clean_text(text)
        assert result == "hello world test"

    def test_clean_text_null_chars(self, normalizer):
        text = "hello\x00world"
        result = normalizer._clean_text(text)
        assert result == "helloworld"

    def test_clean_text_empty(self, normalizer):
        assert normalizer._clean_text("") == ""
        assert normalizer._clean_text(None) == ""

    def test_parse_timestamp_iso(self, normalizer):
        timestamp = "2024-01-15T10:30:00Z"
        result = normalizer._parse_timestamp(timestamp)
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_timestamp_with_ms(self, normalizer):
        timestamp = "2024-01-15T10:30:00.123Z"
        result = normalizer._parse_timestamp(timestamp)
        assert isinstance(result, datetime)

    def test_parse_timestamp_invalid(self, normalizer):
        timestamp = "invalid-date"
        result = normalizer._parse_timestamp(timestamp)
        assert result is None

    def test_normalize_comment(self, normalizer):
        raw = {
            "platform_id": "comment123",
            "text": "Great post!",
            "published_at": "2024-01-15T10:30:00Z",
            "likes": 5
        }

        result = normalizer.normalize_comment(
            raw, "facebook", "post123", "author123"
        )

        assert result.platform == "facebook"
        assert result.platform_id == "comment123"
        assert result.text == "Great post!"
        assert result.post_id == "post123"
        assert result.author_id == "author123"
```

### Validation Tests

```python
# tests/unit/test_models/test_validation.py

import pytest
from pydantic import ValidationError
from src.models.comment import Comment
from datetime import datetime

class TestCommentValidation:
    def test_valid_comment(self):
        comment = Comment(
            platform="facebook",
            platform_id="123",
            post_id="post456",
            author_id="author789",
            text="Valid comment",
            published_at=datetime.utcnow(),
            likes=5
        )
        assert comment.text == "Valid comment"

    def test_empty_text_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            Comment(
                platform="facebook",
                platform_id="123",
                post_id="post456",
                author_id="author789",
                text="",
                published_at=datetime.utcnow()
            )
        assert "text" in str(exc_info.value)

    def test_negative_likes_fails(self):
        with pytest.raises(ValidationError):
            Comment(
                platform="facebook",
                platform_id="123",
                post_id="post456",
                author_id="author789",
                text="Valid",
                likes=-1
            )

    def test_invalid_platform_fails(self):
        with pytest.raises(ValidationError):
            Comment(
                platform="invalid_platform",
                platform_id="123",
                post_id="post456",
                text="Valid"
            )
```

## Integration Tests

### API Tests

```python
# tests/integration/test_api/test_extractions.py

import pytest
from httpx import AsyncClient
from src.api.app import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test_api_key"}

class TestExtractionsAPI:
    @pytest.mark.asyncio
    async def test_create_extraction_success(self, client, auth_headers):
        response = await client.post(
            "/api/v1/extractions",
            json={
                "company_id": "comp_123",
                "platforms": ["facebook", "instagram"]
            },
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_create_extraction_invalid_platform(self, client, auth_headers):
        response = await client.post(
            "/api/v1/extractions",
            json={
                "company_id": "comp_123",
                "platforms": ["invalid"]
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_get_extraction_status(self, client, auth_headers):
        # First create an extraction
        create_response = await client.post(
            "/api/v1/extractions",
            json={
                "company_id": "comp_123",
                "platforms": ["facebook"]
            },
            headers=auth_headers
        )
        job_id = create_response.json()["job_id"]

        # Get status
        response = await client.get(
            f"/api/v1/extractions/{job_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_get_extraction_not_found(self, client, auth_headers):
        response = await client.get(
            "/api/v1/extractions/nonexistent",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthorized_request(self, client):
        response = await client.post(
            "/api/v1/extractions",
            json={"company_id": "comp_123", "platforms": ["facebook"]}
        )

        assert response.status_code == 401
```

### Database Tests

```python
# tests/integration/test_database/test_repositories.py

import pytest
from src.storage.repositories import CommentRepository, JobRepository
from src.models.comment import Comment

@pytest.fixture
async def db_session():
    # Setup test database
    async with get_test_db() as session:
        yield session
        # Cleanup
        await session.rollback()

class TestCommentRepository:
    @pytest.mark.asyncio
    async def test_save_comment(self, db_session):
        repo = CommentRepository(db_session)

        comment = Comment(
            platform="facebook",
            platform_id="123",
            post_id="post456",
            author_id="author789",
            text="Test comment",
            likes=5
        )

        saved = await repo.save(comment)
        assert saved.id is not None

    @pytest.mark.asyncio
    async def test_get_comments_by_job(self, db_session):
        repo = CommentRepository(db_session)

        # Create test comments
        for i in range(10):
            await repo.save(Comment(
                job_id="job123",
                platform="facebook",
                platform_id=f"comment_{i}",
                post_id="post456",
                text=f"Comment {i}"
            ))

        # Retrieve
        comments = await repo.get_by_job("job123")
        assert len(comments) == 10

    @pytest.mark.asyncio
    async def test_get_comments_pagination(self, db_session):
        repo = CommentRepository(db_session)

        # Create 25 comments
        for i in range(25):
            await repo.save(Comment(
                job_id="job123",
                platform="facebook",
                platform_id=f"comment_{i}",
                text=f"Comment {i}"
            ))

        # Page 1
        page1 = await repo.get_by_job("job123", page=1, per_page=10)
        assert len(page1) == 10

        # Page 2
        page2 = await repo.get_by_job("job123", page=2, per_page=10)
        assert len(page2) == 10

        # Page 3
        page3 = await repo.get_by_job("job123", page=3, per_page=10)
        assert len(page3) == 5
```

## E2E Tests

```python
# tests/e2e/test_full_extraction.py

import pytest
import asyncio
from httpx import AsyncClient
from src.api.app import app

@pytest.mark.e2e
class TestFullExtraction:
    @pytest.mark.asyncio
    async def test_complete_extraction_flow(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": "Bearer test_api_key"}

            # 1. Create company
            company_response = await client.post(
                "/api/v1/companies",
                json={
                    "name": "Test Company",
                    "social_accounts": [
                        {
                            "platform": "facebook",
                            "identifier": "testpage"
                        }
                    ]
                },
                headers=headers
            )
            assert company_response.status_code == 201
            company_id = company_response.json()["id"]

            # 2. Start extraction
            extraction_response = await client.post(
                "/api/v1/extractions",
                json={
                    "company_id": company_id,
                    "platforms": ["facebook"]
                },
                headers=headers
            )
            assert extraction_response.status_code == 202
            job_id = extraction_response.json()["job_id"]

            # 3. Wait for completion (with timeout)
            for _ in range(60):  # 60 second timeout
                status_response = await client.get(
                    f"/api/v1/extractions/{job_id}",
                    headers=headers
                )
                status = status_response.json()["status"]

                if status == "completed":
                    break
                elif status == "failed":
                    pytest.fail("Extraction failed")

                await asyncio.sleep(1)
            else:
                pytest.fail("Extraction timeout")

            # 4. Create export
            export_response = await client.post(
                "/api/v1/exports",
                json={
                    "job_id": job_id,
                    "format": "json"
                },
                headers=headers
            )
            assert export_response.status_code == 202
            export_id = export_response.json()["export_id"]

            # 5. Download export
            download_response = await client.get(
                f"/api/v1/exports/{export_id}/download",
                headers=headers
            )
            assert download_response.status_code == 200
            assert len(download_response.content) > 0
```

## Test Fixtures

### Sample Data Fixtures

```python
# tests/conftest.py

import pytest
import json
from pathlib import Path

@pytest.fixture
def facebook_post_fixture():
    return {
        "postId": "123456789_987654321",
        "text": "Check out our new plans!",
        "time": "2024-01-15T10:30:00Z",
        "url": "https://facebook.com/personalpy/posts/987654321",
        "likes": 1200,
        "comments": 89,
        "shares": 150
    }

@pytest.fixture
def facebook_comment_fixture():
    return {
        "id": "987654321_111222333",
        "text": "Great service!",
        "date": "2024-01-15T11:45:00Z",
        "profileId": "444555666",
        "profileName": "Juan Perez",
        "profileUrl": "https://facebook.com/juan.perez",
        "likesCount": 5
    }

@pytest.fixture
def sample_comments():
    """Load sample comments from fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_comments.json"
    with open(fixture_path) as f:
        return json.load(f)

@pytest.fixture
async def test_database():
    """Create and teardown test database."""
    from src.config.database import create_test_database

    db_url = await create_test_database()
    yield db_url
    await drop_test_database(db_url)
```

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/ -m "not slow"

# E2E tests
pytest tests/e2e/ -m e2e

# Specific test file
pytest tests/unit/test_extractors/test_facebook.py

# Specific test
pytest tests/unit/test_extractors/test_facebook.py::TestFacebookExtractor::test_get_posts_success

# Parallel execution
pytest -n auto

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

## Test Configuration

```ini
# pytest.ini

[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests

addopts =
    --strict-markers
    -ra
    --tb=short
```

## Coverage Requirements

- **Overall**: >= 80%
- **Extractors**: >= 90%
- **API endpoints**: >= 85%
- **Models**: >= 95%
