# API Contract Validator Skill

Validate API contracts, OpenAPI specs, and ensure endpoint consistency for FastAPI applications.

## Metadata

- Name: API Contract Validator
- Category: API & Integration Testing
- Activation: Automatic when API validation mentioned
- Model: Haiku (fast validation) or Sonnet (deep analysis)
- Token Cost: ~800 tokens

## When to Activate

Trigger this skill when user mentions:
- "Validate API contract"
- "Check OpenAPI spec"
- "API endpoint validation"
- "Request/response schema"
- "API documentation"
- "Endpoint consistency"
- "Test API example"

## Core Capabilities

### 1. Request/Response Schema Validation

Validate that:
- Request schemas match Pydantic models
- Response schemas documented correctly
- Optional vs required fields consistent
- Type annotations accurate
- Default values make sense

### 2. Endpoint Consistency Checking

Verify:
- HTTP methods match operations (GET=read, POST=create)
- URL patterns follow REST conventions
- Status codes appropriate for operations
- Error responses standardized
- Authentication requirements documented

### 3. OpenAPI Spec Generation

Ensure:
- Auto-generated docs accurate
- Examples work with real data
- Deprecation warnings present
- Tags organized logically
- Descriptions comprehensive

### 4. Example Request Testing

Test that:
- Example requests in docs actually work
- Response examples match real responses
- Edge cases documented
- Error cases covered

## Project-Specific Context

### Current API Setup

```python
# Customer Feedback Analyzer API
Framework: FastAPI 0.109.0
Docs: Auto-generated at /docs (Swagger UI)
Spec: OpenAPI 3.1.0
Base URL: /api/v1
```

### Existing Endpoints

1. POST /api/v1/upload
   - Upload CSV/Excel file
   - Returns: task_id
   - Status codes: 200 (success), 415 (invalid format), 413 (too large)

2. GET /api/v1/status/task_id
   - Check analysis status
   - Returns: status, progress, result_url
   - Status codes: 200 (success), 404 (not found)

3. POST /api/v1/analyze
   - Direct analysis without file upload
   - Returns: analysis results
   - Status codes: 200 (success), 422 (validation error)

### Pydantic Schemas

Located in api/app/schemas/:
- UploadResponse
- TaskStatus
- AnalysisRequest
- AnalysisResponse
- ErrorResponse

## Usage Examples

### Example 1: Validate Upload Endpoint

```
User: Validate the upload endpoint API contract

Skill checks:

1. Request Schema Validation:

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    ...

Issues found:
- Missing file size limit documentation
- No content-type validation in schema
- Error responses not documented

Recommendations:
1. Add file size limit to OpenAPI description
2. Document supported MIME types
3. Add error response examples

Fixed endpoint:

@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        200: {
            "description": "File uploaded successfully",
            "content": {
                "application/json": {
                    "example": {"task_id": "task_123", "status": "processing"}
                }
            }
        },
        413: {
            "description": "File too large (max 10MB)",
            "model": ErrorResponse
        },
        415: {
            "description": "Unsupported file format (use .csv or .xlsx)",
            "model": ErrorResponse
        }
    },
    summary="Upload customer feedback file",
    description="Upload CSV or Excel file for analysis. Max file size: 10MB."
)
async def upload_file(
    file: UploadFile = File(..., description="CSV or Excel file containing feedback")
):
    ...
```

### Example 2: Schema Consistency Check

```
User: Check if request/response schemas are consistent

Skill validates:

1. Pydantic Model Definition (api/app/schemas/upload.py):

from pydantic import BaseModel, Field

class UploadResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Current status (processing, completed, failed)")
    estimated_time: Optional[int] = Field(None, description="Estimated completion time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "status": "processing",
                "estimated_time": 45
            }
        }

2. Endpoint Implementation Check:

Issues found:
- Implementation returns "message" field not in schema
- Schema defines estimated_time but implementation never sets it
- Status enum values not enforced

Fixed schema:

from enum import Enum

class TaskStatusEnum(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadResponse(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=100)
    status: TaskStatusEnum  # Enum instead of string
    estimated_time: Optional[int] = Field(None, ge=0, le=3600)  # 0-3600 seconds

    class Config:
        use_enum_values = True
```

### Example 3: Error Response Standardization

```
User: Standardize error responses across all endpoints

Skill generates:

1. Standard Error Schema (api/app/schemas/errors.py):

from pydantic import BaseModel
from typing import Optional, List

class ValidationDetail(BaseModel):
    loc: List[str]  # Field location (e.g., ["body", "file"])
    msg: str        # Error message
    type: str       # Error type (e.g., "value_error.missing")

class ErrorResponse(BaseModel):
    error: str  # Human-readable error message
    code: str   # Machine-readable error code (FILETOOLARGE, INVALIDFORMAT, etc.)
    details: Optional[List[ValidationDetail]] = None  # Validation errors
    path: str   # Request path
    task_id: Optional[str] = None  # Task ID if applicable

    class Config:
        json_schema_extra = {
            "example": {
                "error": "File size 15728640 exceeds maximum 10485760",
                "code": "FILETOOLARGEERROR",
                "path": "/api/v1/upload",
                "task_id": None
            }
        }

2. Apply to All Endpoints:

@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Invalid file format"},
        422: {"model": ErrorResponse, "description": "Validation error"}
    }
)

@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"}
    }
)
```

## Best Practices Enforced

### 1. Use Pydantic Field Validators

```python
from pydantic import BaseModel, Field, field_validator

class AnalysisRequest(BaseModel):
    comments: List[str] = Field(..., min_length=1, max_length=1000)
    language: str = Field(default="es", pattern="^(es|en)$")

    @field_validator('comments')
    @classmethod
    def validate_comments(cls, v):
        if not v:
            raise ValueError("At least one comment required")
        if any(len(comment) > 5000 for comment in v):
            raise ValueError("Comment too long (max 5000 characters)")
        return v
```

### 2. Document All Query Parameters

```python
@router.get("/analysis")
async def get_analysis(
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("created_at", regex="^(created_at|score|churn_risk)$"),
    order: str = Query("desc", regex="^(asc|desc)$")
):
    ...
```

### 3. Use Response Models for Type Safety

```python
# Bad - Returns dict (no validation)
@router.get("/stats")
async def get_stats():
    return {"count": 100, "average": 7.5}

# Good - Returns Pydantic model (validated)
class StatsResponse(BaseModel):
    count: int = Field(..., ge=0)
    average: float = Field(..., ge=0, le=10)
    median: float = Field(..., ge=0, le=10)

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(count=100, average=7.5, median=8.0)
```

### 4. HTTP Status Code Conventions

```python
# GET endpoints
200: Success
404: Not found
422: Validation error

# POST endpoints (create)
201: Created
400: Bad request
422: Validation error

# PUT endpoints (update)
200: Success
404: Not found
422: Validation error

# DELETE endpoints
204: No content (success)
404: Not found
```

## Validation Checklist

Before API release, verify:

- [ ] All endpoints have response_model defined
- [ ] Error responses documented for all status codes
- [ ] Request validation uses Pydantic Field constraints
- [ ] Examples in OpenAPI spec work with real data
- [ ] Authentication requirements documented
- [ ] Rate limiting documented
- [ ] Deprecation warnings for old endpoints
- [ ] CORS configuration correct
- [ ] API versioning consistent
- [ ] Response compression enabled for large payloads

## Testing Strategy

### 1. Schema Validation Tests

```python
# api/tests/api/test_upload_schema.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_response_schema():
    response = client.post("/api/v1/upload", files={"file": ("test.csv", b"content")})

    assert response.status_code == 200
    data = response.json()

    # Validate required fields
    assert "task_id" in data
    assert "status" in data

    # Validate types
    assert isinstance(data["task_id"], str)
    assert data["status"] in ["processing", "completed", "failed"]

def test_error_response_schema():
    response = client.post("/api/v1/upload")  # Missing file

    assert response.status_code == 422
    data = response.json()

    # Validate error structure
    assert "error" in data
    assert "code" in data
    assert "path" in data
```

### 2. Example Request Tests

```python
def test_openapi_examples_work():
    # Get OpenAPI spec
    response = client.get("/openapi.json")
    spec = response.json()

    # Test each example request
    for path, methods in spec["paths"].items():
        for method, details in methods.items():
            if "requestBody" in details:
                example = details["requestBody"]["content"]["application/json"]["example"]

                # Make request with example
                response = client.request(method, path, json=example)

                # Should not be 500 (server error)
                assert response.status_code != 500
```

### 3. Contract Testing

```python
# Use pact for consumer-driven contract testing
from pact import Consumer, Provider

pact = Consumer('feedback-analyzer-frontend').has_pact_with(
    Provider('feedback-analyzer-api')
)

def test_upload_contract():
    (pact
     .given('file upload endpoint available')
     .upon_receiving('a file upload request')
     .with_request('POST', '/api/v1/upload')
     .will_respond_with(200, body={
         'task_id': 'task_123',
         'status': 'processing'
     }))

    with pact:
        response = requests.post('http://localhost:8000/api/v1/upload', files={'file': ...})
        assert response.json()['task_id'] == 'task_123'
```

## Common Issues

### Issue 1: Optional Fields Not Truly Optional

```python
# Problem
class AnalysisRequest(BaseModel):
    language: Optional[str] = None  # But actually required in implementation

# Solution
class AnalysisRequest(BaseModel):
    language: str = Field(default="es")  # Explicit default
```

### Issue 2: Inconsistent Error Responses

```python
# Problem - Different endpoints return different error formats
# Endpoint 1:
{"message": "File not found"}

# Endpoint 2:
{"error": "Invalid format", "details": ["..."]}

# Solution - Standardize with ErrorResponse schema
{"error": "...", "code": "...", "path": "...", "task_id": None}
```

### Issue 3: Missing Validation

```python
# Problem
@router.post("/analyze")
async def analyze(comments: List[str]):  # No length limits!
    ...

# Solution
@router.post("/analyze")
async def analyze(
    comments: List[str] = Body(..., min_length=1, max_length=100)
):
    ...
```

## OpenAPI Documentation

### 1. Add Metadata

```python
from fastapi import FastAPI

app = FastAPI(
    title="Customer Feedback Analyzer API",
    description="AI-powered customer feedback analysis with sentiment, churn risk, and pain point detection",
    version="3.9.0",
    contact={
        "name": "API Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT"
    }
)
```

### 2. Tag Endpoints

```python
@router.post("/upload", tags=["File Operations"])
@router.get("/status/{task_id}", tags=["Task Management"])
@router.post("/analyze", tags=["Analysis"])
```

### 3. Add Security Schemes

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@router.get(
    "/protected",
    dependencies=[Depends(security)],
    responses={
        401: {"description": "Unauthorized"}
    }
)
async def protected_endpoint():
    ...
```

## Quick Reference

```bash
# View OpenAPI spec
curl http://localhost:8000/openapi.json

# Access Swagger UI
open http://localhost:8000/docs

# Access ReDoc
open http://localhost:8000/redoc

# Validate OpenAPI spec
npm install -g @stoplight/spectral-cli
spectral lint openapi.json

# Generate client SDK
openapi-generator-cli generate -i openapi.json -g python -o sdk/
```

## Success Criteria

API contract is valid when:

- [ ] All endpoints have Pydantic response models
- [ ] Error responses standardized
- [ ] Request validation comprehensive
- [ ] OpenAPI examples tested and working
- [ ] Authentication documented
- [ ] HTTP status codes appropriate
- [ ] Field-level validation with constraints
- [ ] Optional vs required fields clear
- [ ] Type annotations accurate
- [ ] Tests cover schema validation

## Related Files

- [api/app/api/endpoints/](../../../api/app/api/endpoints/) - API endpoints
- [api/app/schemas/](../../../api/app/schemas/) - Pydantic schemas
- [api/tests/api/](../../../api/tests/api/) - API tests
- [api/app/main.py](../../../api/app/main.py) - FastAPI app setup

## Version

Last Updated: 2025-11-16
Status: Ready for use
