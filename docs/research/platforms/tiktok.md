# TikTok Data Extraction Research

## Overview
TikTok has grown significantly for business marketing, especially for younger demographics. Telecom companies increasingly use TikTok for brand awareness and customer engagement.

## Official API: TikTok API

### Research API (Academic/Research)
- Available for verified researchers
- Access to public video data
- Strict application process
- Limited commercial use

### Marketing API
- For advertising purposes
- Campaign management
- Performance metrics
- Not for content scraping

### Display API
- Embed TikTok content
- Limited data access
- No comment extraction

### Limitations
Official TikTok APIs are very restrictive for comment extraction:
- No public endpoint for scraping comments
- Designed primarily for content creation and ads
- Research API requires academic verification

## Third-Party Solutions (Primary Approach)

### Apify TikTok Comment Scraper

#### Pricing
- **$0.20 per 1,000 comments** (approx)
- Free tier available with Apify credits

#### Features
- No authentication required
- Fast extraction
- Includes nested replies
- Engagement metrics

```python
# Output structure
{
    "comment_id": "7012345678901234567",
    "text": "Love this!",
    "create_time": 1705312200,
    "user": {
        "id": "987654321",
        "unique_id": "user123",
        "nickname": "User Name",
        "avatar_url": "https://..."
    },
    "likes_count": 150,
    "reply_count": 5,
    "is_pinned": false
}
```

### Apify Actors Available
1. **clockworks/tiktok-comments-scraper** - Standard scraper
2. **novi/tiktok-comment-api** - Blazing fast API
3. **epctex/tiktok-comment-scraper** - Alternative
4. **codescraper/tiktok-comments-scraper** - Another option

### Bright Data TikTok Scraper
- Proxy infrastructure included
- High reliability
- Usage-based pricing

### Crawlbase
- API-based approach
- Handles anti-bot measures
- Requires API key

## Technical Approach

### Using Apify
```python
from apify_client import ApifyClient

def scrape_tiktok_comments(video_urls):
    client = ApifyClient("YOUR_API_KEY")

    run_input = {
        "postURLs": video_urls,
        "maxComments": 1000,
        "maxRepliesPerComment": 100
    }

    run = client.actor("clockworks/tiktok-comments-scraper").call(run_input=run_input)

    comments = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        comments.append(item)

    return comments
```

### Direct Scraping (Complex)
TikTok uses aggressive anti-bot measures:
- Device fingerprinting
- Signature validation
- Rate limiting
- CAPTCHA challenges

Not recommended without significant infrastructure investment.

## Legal Considerations

### Terms of Service
- TikTok prohibits automated data collection
- Third-party scrapers operate in gray area
- Public data scraping generally legal
- Must comply with privacy regulations

### Best Practices
- Use reputable third-party services
- Don't collect unnecessary personal data
- Implement data retention policies
- Be transparent about data usage

## Data Schema

### Video Object
```json
{
  "video_id": "7012345678901234567",
  "desc": "Check out our new 5G coverage! #PersonalPy #5G",
  "create_time": 1705312200,
  "author": {
    "id": "123456789",
    "unique_id": "personalpy",
    "nickname": "Personal Paraguay",
    "verified": true
  },
  "statistics": {
    "play_count": 50000,
    "like_count": 3500,
    "comment_count": 234,
    "share_count": 150
  },
  "music": {
    "id": "6821123456789",
    "title": "Original Sound"
  }
}
```

### Comment Object
```json
{
  "comment_id": "7012345678901234568",
  "text": "Finally 5G in my area!",
  "create_time": 1705315800,
  "user": {
    "id": "987654321",
    "unique_id": "user123",
    "nickname": "Juan Perez",
    "avatar_url": "https://p16-sign-va.tiktokcdn.com/..."
  },
  "likes_count": 89,
  "reply_count": 5,
  "is_author_liked": true,
  "replies": [
    {
      "comment_id": "7012345678901234569",
      "text": "Which city?",
      "user": {...}
    }
  ]
}
```

## Estimated Volume for Personal Paraguay
- **Videos per month**: 10-30 (if active on platform)
- **Views per video**: 5,000-100,000
- **Comments per video**: 50-500
- **Total comments to process**: 500-10,000 per month

## Unique Characteristics

### TikTok Comment Patterns
- Shorter comments
- More emojis and slang
- Younger demographic
- Memes and trends
- Duet/stitch references
- Question-focused

### Valuable Insights
- Brand perception among youth
- Viral content performance
- Trend adoption
- Competitor comparison
- Service area questions

## Challenge Considerations

### High Volume Potential
- TikTok videos can go viral
- Single video might get 1000s of comments
- Need pagination handling
- Storage considerations

### Language/Content
- Mix of Spanish and Guaraní
- Informal language
- Slang and abbreviations
- Requires specialized NLP for Paraguay
