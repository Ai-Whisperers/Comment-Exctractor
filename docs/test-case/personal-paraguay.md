# Test Case: Personal Paraguay

## Company Overview

### Basic Information
- **Company Name**: Personal Paraguay (Núcleo S.A.)
- **Industry**: Telecommunications
- **Founded**: June 24, 1998
- **Country**: Paraguay
- **Headquarters**: 224 Avda. España, Asunción, Paraguay
- **Website**: www.personal.com.py

### Ownership Structure
- 32.5% ABC Comunicaciones (Paraguayan group)
- 67.5% Telecom Personal (part of Telecom Italia Mobile group)

### Services Offered
- Mobile telephony (prepaid and postpaid)
- High-speed fiber internet
- TV streaming (Flow)
- Personal Pay (payment services)
- Business solutions

## Social Media Presence

### Active Accounts

| Platform | Handle | URL | Followers | Status |
|----------|--------|-----|-----------|--------|
| Facebook | @personalpy | https://www.facebook.com/personalpy | 495,428 | Active |
| Instagram | @personalpy | https://www.instagram.com/personalpy | 110,000 | Active (2,497 posts) |
| Twitter/X | @personalpy | https://twitter.com/personalpy | TBD | Active |
| LinkedIn | Personal Paraguay | https://linkedin.com/company/personalparaguay | 60,674 | Active |
| TikTok | TBD | TBD | TBD | TBD |

### Platform Usage Patterns

#### Facebook
- **Primary Use**: Customer service, promotions, brand awareness
- **Post Frequency**: 1-3 posts per day
- **Content Types**: Promotional offers, service announcements, contests
- **Engagement**: High comment volume, customer complaints

#### Instagram
- **Primary Use**: Lifestyle marketing, visual content
- **Post Frequency**: 2-4 posts per day
- **Content Types**: Reels, stories, product shots, influencer content
- **Engagement**: Good engagement on reels, younger audience

#### Twitter/X
- **Primary Use**: Customer service, real-time support
- **Post Frequency**: Multiple times daily
- **Content Types**: Service updates, responses, quick announcements
- **Engagement**: Complaint-heavy, fast response expected

#### LinkedIn
- **Primary Use**: B2B marketing, corporate communications, hiring
- **Post Frequency**: 2-3 times per week
- **Content Types**: Corporate news, job postings, business solutions
- **Engagement**: Professional audience, lower volume

## Expected Data Characteristics

### Volume Estimates

| Metric | Monthly Low | Monthly High |
|--------|-------------|--------------|
| Facebook comments | 5,000 | 30,000 |
| Instagram comments | 2,000 | 10,000 |
| Twitter replies | 1,000 | 5,000 |
| LinkedIn comments | 100 | 500 |
| **Total** | **8,100** | **45,500** |

### Language Distribution
- **Spanish**: 85-90%
- **Guaraní**: 5-10%
- **Mixed (Jopará)**: 3-5%
- **Portuguese/English**: 1-2%

### Sentiment Expectations

Based on telecom industry patterns:
- **Positive**: 20-30% (promotions, coverage expansion, good service)
- **Negative**: 50-60% (complaints dominate social media)
- **Neutral**: 15-25% (questions, general inquiries)

### Common Topics

#### Positive Topics
1. New plan announcements
2. Coverage expansion
3. Promotional offers
4. Speed improvements
5. New features/services

#### Negative Topics
1. Internet speed issues
2. Poor coverage areas
3. Billing problems
4. Customer service complaints
5. Service outages
6. App issues
7. Roaming charges

#### Neutral Topics
1. Plan inquiries
2. Coverage questions
3. Store locations
4. Technical support requests
5. Account management

## Sample Data Scenarios

### Scenario 1: Normal Week
```json
{
  "period": "2024-01-15 to 2024-01-21",
  "facebook_posts": 15,
  "facebook_comments": 1200,
  "instagram_posts": 20,
  "instagram_comments": 600,
  "twitter_posts": 30,
  "twitter_replies": 400,
  "sentiment_distribution": {
    "positive": 25,
    "negative": 55,
    "neutral": 20
  },
  "top_issues": [
    "internet_speed",
    "billing",
    "customer_service"
  ]
}
```

### Scenario 2: Service Outage
```json
{
  "period": "2024-01-22 (outage day)",
  "comment_spike": "5x normal volume",
  "facebook_comments": 3000,
  "twitter_replies": 2000,
  "sentiment_distribution": {
    "positive": 5,
    "negative": 90,
    "neutral": 5
  },
  "dominant_issues": [
    "service_outage",
    "no_signal",
    "internet_down"
  ],
  "geographic_concentration": [
    "Asunción",
    "Central"
  ]
}
```

### Scenario 3: Promotional Campaign
```json
{
  "period": "2024-02-01 to 2024-02-07 (promo week)",
  "facebook_posts": 25,
  "facebook_comments": 2500,
  "instagram_posts": 35,
  "instagram_comments": 1500,
  "sentiment_distribution": {
    "positive": 45,
    "negative": 35,
    "neutral": 20
  },
  "top_topics": [
    "new_plan",
    "discount",
    "switch_carrier"
  ]
}
```

## Test Extraction Configuration

### Input Configuration

```python
test_config = {
    "company": {
        "name": "Personal Paraguay",
        "industry": "Telecommunications",
        "country": "Paraguay"
    },
    "social_accounts": {
        "facebook": {
            "page_id": "personalpy",
            "url": "https://www.facebook.com/personalpy"
        },
        "instagram": {
            "username": "personalpy",
            "url": "https://www.instagram.com/personalpy"
        },
        "twitter": {
            "username": "personalpy",
            "url": "https://twitter.com/personalpy"
        },
        "linkedin": {
            "company_id": "personalparaguay",
            "url": "https://linkedin.com/company/personalparaguay"
        }
    },
    "extraction_params": {
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-01-31"
        },
        "max_posts_per_platform": 100,
        "max_comments_per_post": 500,
        "include_replies": True
    }
}
```

### Expected Output Structure

```python
expected_output = {
    "extraction_summary": {
        "total_posts": 200,
        "total_comments": 15000,
        "unique_commenters": 8000,
        "platforms_processed": 4,
        "date_range": "2024-01-01 to 2024-01-31"
    },
    "platform_breakdown": {
        "facebook": {
            "posts": 60,
            "comments": 8000,
            "avg_comments_per_post": 133
        },
        "instagram": {
            "posts": 80,
            "comments": 4000,
            "avg_comments_per_post": 50
        },
        "twitter": {
            "posts": 50,
            "comments": 2500,
            "avg_comments_per_post": 50
        },
        "linkedin": {
            "posts": 10,
            "comments": 500,
            "avg_comments_per_post": 50
        }
    }
}
```

## Analysis Test Cases

### Test Case 1: Sentiment Accuracy

**Objective**: Verify sentiment analysis accuracy for Spanish telecom context

**Test Data**:
```python
test_comments = [
    {
        "text": "Excelente servicio, muy rápido el internet",
        "expected_sentiment": "POS",
        "confidence_threshold": 0.8
    },
    {
        "text": "Pésimo, nunca funciona la señal",
        "expected_sentiment": "NEG",
        "confidence_threshold": 0.8
    },
    {
        "text": "Cuánto cuesta el plan de 50GB?",
        "expected_sentiment": "NEU",
        "confidence_threshold": 0.6
    },
    {
        "text": "Internet lentísimo, no sirve para nada",
        "expected_sentiment": "NEG",
        "confidence_threshold": 0.9
    },
    {
        "text": "Gracias por expandir la cobertura a mi zona!",
        "expected_sentiment": "POS",
        "confidence_threshold": 0.85
    }
]
```

### Test Case 2: Deduplication

**Objective**: Correctly identify and group similar comments

**Test Data**:
```python
duplicate_groups = [
    {
        "representative": "El internet está muy lento",
        "variants": [
            "Internet muy lento",
            "Muy lento el internet",
            "El internet es lentisimo",
            "Internet lento"
        ],
        "expected_group_size": 5
    },
    {
        "representative": "No tengo señal",
        "variants": [
            "Sin señal",
            "No hay señal",
            "Se fue la señal",
            "Estoy sin señal"
        ],
        "expected_group_size": 5
    }
]
```

### Test Case 3: Commenter Classification

**Objective**: Correctly classify commenter types

**Test Profiles**:
```python
test_commenters = [
    {
        "username": "super_fan_user",
        "total_comments": 25,
        "positive_ratio": 0.8,
        "expected_classification": "super_fan"
    },
    {
        "username": "chronic_complainer",
        "total_comments": 15,
        "negative_ratio": 0.85,
        "expected_classification": "frequent_negative"
    },
    {
        "username": "occasional_user",
        "total_comments": 4,
        "positive_ratio": 0.5,
        "expected_classification": "occasional"
    },
    {
        "username": "one_time_user",
        "total_comments": 1,
        "expected_classification": "one_time"
    }
]
```

### Test Case 4: Topic Clustering

**Objective**: Identify main discussion topics

**Expected Clusters**:
```python
expected_clusters = [
    {
        "theme": "Internet Speed Issues",
        "keywords": ["lento", "velocidad", "mbps", "internet"],
        "min_percentage": 15
    },
    {
        "theme": "Coverage Problems",
        "keywords": ["cobertura", "señal", "zona", "red"],
        "min_percentage": 10
    },
    {
        "theme": "Billing/Charges",
        "keywords": ["cobro", "factura", "pago", "saldo"],
        "min_percentage": 8
    },
    {
        "theme": "Customer Service",
        "keywords": ["atención", "servicio", "llamar", "responder"],
        "min_percentage": 5
    },
    {
        "theme": "Promotional Inquiries",
        "keywords": ["plan", "precio", "promoción", "descuento"],
        "min_percentage": 10
    }
]
```

## Validation Criteria

### Data Quality Checks

1. **Completeness**
   - All required fields populated
   - No orphan comments (must have post reference)
   - Timestamps in valid format

2. **Consistency**
   - Unique IDs across platform
   - Consistent date formats
   - Valid sentiment scores (0-1 range)

3. **Accuracy**
   - Sentiment analysis > 80% accuracy on test set
   - Cluster coherence score > 0.6
   - No duplicate entries in final output

### Performance Benchmarks

| Operation | Max Time | Notes |
|-----------|----------|-------|
| Extract 1,000 comments | 5 min | With rate limiting |
| Sentiment analysis (1,000) | 2 min | Batch processing |
| Clustering (10,000) | 5 min | Including embeddings |
| Full pipeline (15,000) | 30 min | End to end |

## Sample Output Files

### Sample Cluster Output

```json
{
  "cluster_id": 1,
  "theme": "Internet Speed Complaints",
  "representative_text": "El internet está muy lento, no puedo trabajar desde casa",
  "count": 450,
  "percentage": 3.0,
  "sentiment": "negative",
  "sentiment_score": -0.85,
  "unique_authors": 380,
  "keywords": ["internet", "lento", "velocidad", "mbps", "trabajar"],
  "sample_comments": [
    "Internet lentísimo hoy",
    "La velocidad es pésima, no llega a 2 mbps",
    "Imposible trabajar con este internet",
    "Muy lento el servicio de internet",
    "No sirve el internet para videollamadas"
  ],
  "platforms": {
    "facebook": 200,
    "twitter": 150,
    "instagram": 100
  },
  "peak_dates": ["2024-01-05", "2024-01-15"],
  "locations_mentioned": ["Asunción", "Luque", "San Lorenzo"]
}
```

### Sample Commenter Profile

```json
{
  "commenter_id": "fb_123456789",
  "username": "maria_gonzalez",
  "platforms": ["facebook", "instagram"],
  "total_comments": 18,
  "avg_likes_per_comment": 4.2,
  "classification": "frequent_negative",
  "influence_score": 35.5,
  "sentiment_profile": {
    "positive_ratio": 0.15,
    "negative_ratio": 0.75,
    "neutral_ratio": 0.10
  },
  "primary_issues": ["coverage", "billing"],
  "engagement_pattern": {
    "preferred_hours": [19, 20, 21],
    "preferred_days": ["Monday", "Friday"]
  },
  "journey": {
    "first_contact": "2023-06-15",
    "last_contact": "2024-01-28",
    "sentiment_trend": "stable"
  },
  "sample_comments": [
    "Otra vez sin señal en mi zona",
    "El cobro está mal, no contraté eso",
    "Cuándo van a mejorar la cobertura en Lambaré?"
  ]
}
```

## Next Steps for Implementation

1. **Phase 1: Data Extraction** (Week 1-2)
   - Set up Facebook extraction (highest volume)
   - Test with 1 week of data
   - Validate data schema

2. **Phase 2: Basic Analysis** (Week 3)
   - Implement sentiment analysis
   - Test Spanish model accuracy
   - Basic clustering

3. **Phase 3: Full Pipeline** (Week 4)
   - Add remaining platforms
   - Commenter analysis
   - Report generation

4. **Phase 4: Refinement** (Week 5)
   - Tune clustering parameters
   - Improve deduplication
   - Dashboard creation
