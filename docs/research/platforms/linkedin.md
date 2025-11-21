# LinkedIn Data Extraction Research

## Overview
LinkedIn is crucial for B2B engagement and employer branding. Personal Paraguay has **60,674 followers** on LinkedIn with the tagline "Hacé Más" (Do More).

## Official API: LinkedIn Marketing API

### Endpoints Available

#### Posts API
```
GET https://api.linkedin.com/rest/posts
```
Retrieve organic and sponsored posts from company pages.

#### Comments API
```
GET https://api.linkedin.com/rest/socialActions/{shareUrn}/comments
```
Read comments on shares/posts.

#### Reactions API
```
GET https://api.linkedin.com/rest/socialActions/{shareUrn}/reactions
```
Get reactions (likes, celebrations, etc.) on posts.

### Required Headers
```
Authorization: Bearer {access_token}
Linkedin-Version: 202411  // YYYYMM format
X-Restli-Protocol-Version: 2.0.0
```

### Authentication Requirements
- OAuth 2.0 authentication
- Marketing Developer Platform access
- Required permissions:
  - `r_organization_social` - Read organization posts
  - `w_organization_social` - Write posts (not needed for reading)
  - `rw_organization_admin` - Admin access

### Data Available

#### Post Data
- `id` - Post URN
- `author` - Company/person URN
- `commentary` - Post text
- `publishedAt` - Timestamp
- `content` - Media, articles, documents
- `distribution` - Visibility settings
- `lifecycleState` - Draft, published
- `visibility` - Public, connections, etc.

#### Comment Data
- `id` - Comment URN
- `actor` - Commenter URN
- `message` - Comment text
- `created` - Timestamp
- `likesSummary` - Like counts
- `commentsSummary` - Reply counts

### Permissions Challenge

Common issue:
```
Error: "Not enough permissions to access: GET-owners /shares"
Status: 403
```

This requires:
1. App review by LinkedIn
2. Organization admin access
3. Proper OAuth scopes

### Rate Limits
- 100,000 calls per day (varies by permission level)
- Rate limits are per application

## Third-Party Solutions

### Apify LinkedIn Scrapers

#### LinkedIn Post Comments Scraper
- **Cost**: $1.20 per 1,000 comments
- **No cookies/login required**
- **Features**: Comments, replies, reactions, media

```python
# Output structure
{
    "comment_id": "urn:li:comment:...",
    "text": "Great post!",
    "author": {
        "name": "Juan Perez",
        "headline": "Software Engineer",
        "profile_url": "https://linkedin.com/in/..."
    },
    "timestamp": "2024-01-15T10:30:00.000Z",
    "likes": 5,
    "replies": []
}
```

#### Limitations
- Free tier: 4 posts, 100 comments per post per run
- Full access requires paid plan

### Lix API
- Real-time post data
- Use cases: social listening, content marketing
- Provides: like_count, comments_count, date_published, total_engagement

### Piloterr API
- LinkedIn post data extraction
- Engagement metrics included
- Third-party compliant

## Implementation Approach

### Using Official API
```python
import requests

class LinkedInClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.linkedin.com/rest"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Linkedin-Version": "202411",
            "X-Restli-Protocol-Version": "2.0.0"
        }

    def get_organization_posts(self, org_id):
        url = f"{self.base_url}/posts"
        params = {
            "q": "author",
            "author": f"urn:li:organization:{org_id}",
            "count": 50
        }

        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def get_post_comments(self, post_urn):
        # URL encode the URN
        encoded_urn = requests.utils.quote(post_urn, safe='')
        url = f"{self.base_url}/socialActions/{encoded_urn}/comments"

        params = {
            "count": 100,
            "start": 0
        }

        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def get_post_reactions(self, post_urn):
        encoded_urn = requests.utils.quote(post_urn, safe='')
        url = f"{self.base_url}/socialActions/{encoded_urn}/reactions"

        response = requests.get(url, headers=self.headers)
        return response.json()
```

### Using Apify (No Auth)
```python
from apify_client import ApifyClient

def scrape_linkedin_comments(post_urls):
    client = ApifyClient("YOUR_API_KEY")

    run_input = {
        "postUrls": post_urls,
        "maxComments": 100
    }

    run = client.actor("harvestapi/linkedin-post-comments").call(run_input=run_input)

    comments = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        comments.append(item)

    return comments
```

## Legal Considerations

### Terms of Service
- LinkedIn is strict about scraping
- Official API requires app review
- Unauthorized scraping can result in legal action
- LinkedIn has sued scrapers (hiQ Labs case)

### Best Practices
- Use official API when possible
- For third-party, use reputable services
- Don't scrape personal data unnecessarily
- Implement data retention policies

## Data Schema

### Post Object
```json
{
  "id": "urn:li:share:7012345678901234567",
  "author": "urn:li:organization:123456",
  "commentary": "Discover our new business solutions for enterprises!",
  "publishedAt": 1705312200000,
  "content": {
    "media": {
      "id": "urn:li:image:...",
      "altText": "Business solutions banner"
    }
  },
  "distribution": {
    "feedDistribution": "MAIN_FEED",
    "thirdPartyDistributionChannels": []
  },
  "visibility": "PUBLIC",
  "lifecycleState": "PUBLISHED"
}
```

### Comment Object
```json
{
  "id": "urn:li:comment:7012345678901234568",
  "actor": "urn:li:person:ABC123",
  "message": {
    "text": "This is exactly what we needed!"
  },
  "created": {
    "time": 1705315800000
  },
  "likesSummary": {
    "totalLikes": 8
  },
  "commentsSummary": {
    "totalFirstLevelComments": 2
  },
  "author_details": {
    "name": "Maria Gonzalez",
    "headline": "IT Manager at TechCorp",
    "company": "TechCorp Paraguay"
  }
}
```

## Estimated Volume for Personal Paraguay
- **Followers**: ~60,674
- **Posts per month**: 10-30 (B2B focus)
- **Comments per post**: 5-50 (lower than consumer platforms)
- **Engagement type**: More professional, B2B inquiries
- **Total comments to process**: 100-1,000 per month

## Unique Value for LinkedIn

### B2B Insights
- Company decision-makers commenting
- Business partnership opportunities
- Employer brand perception
- Industry thought leadership

### Comment Characteristics
- More formal language
- Business inquiries
- Job seekers
- Industry professionals
- Less complaint-focused than other platforms
