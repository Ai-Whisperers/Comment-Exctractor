# Instagram Data Extraction Research

## Overview
Instagram is owned by Meta and has become crucial for business engagement. Personal Paraguay (@personalpy) has **110K followers**, follows **303 accounts**, and has **2,497 posts**.

## Official API: Instagram Graph API

### Important Note
On **September 4, 2024**, Meta announced the **Instagram Basic Display API deprecation**. Only the Instagram Graph API remains for business/creator accounts.

### Endpoints Available

#### Media (Posts)
```
GET /{ig-user-id}/media
```
Returns media objects (posts, reels, stories) for a business account.

#### Comments
```
GET /{media-id}/comments
```
Returns comments on a specific media object.

### Authentication Requirements
- Facebook App with Instagram Graph API enabled
- **Permissions**:
  - `instagram_basic`
  - `instagram_manage_comments`
  - `pages_read_engagement`
- Business or Creator Instagram account linked to Facebook Page

### Data Available

#### Media (Post) Data
- `id` - Media identifier
- `caption` - Post caption
- `media_type` - IMAGE, VIDEO, CAROUSEL_ALBUM
- `media_url` - Direct URL to media
- `permalink` - Instagram URL
- `timestamp` - Posted time
- `like_count` - Number of likes
- `comments_count` - Number of comments
- `username` - Account username

#### Comment Data
- `id` - Comment identifier
- `text` - Comment content
- `timestamp` - Time posted
- `username` - Commenter username
- `like_count` - Likes on comment
- `replies` - Nested replies (if any)

### Critical Limitations

1. **Own Account Only**: Can only access data for accounts you manage
2. **No Third-Party Access**: Cannot retrieve posts/comments from other business accounts
3. **No User Metadata**: Cannot access commenter profile info for non-managed accounts
4. **No Hashtag Search**: Cannot search by hashtag without special permissions

## Third-Party Solutions

### Apify Instagram Scraper
- **Cost**: $2.30 per 1,000 comments
- **Free tier**: $5/month (2,100+ comments)
- **No authentication**: Works on public profiles
- **Data**: Posts, comments, profiles, reels

### Features Available
```python
# Data points from Apify scraper
{
    "comment_id": "17895695668004550",
    "text": "Love this!",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "owner_username": "user123",
    "owner_id": "12345678",
    "owner_profile_pic_url": "https://...",
    "is_verified": false,
    "like_count": 5,
    "reply_count": 2
}
```

### Bright Data Instagram Scraper
- Scrapes public Instagram profiles
- Data: post ID, text, position, timestamp, username
- Proxy infrastructure included

### Phyllo API
- Built on Instagram's authorized APIs
- Access to: profiles, posts, comments, likes, engagement metrics
- Compliant with platform policies

## Technical Approach: GraphQL

Instagram uses GraphQL internally. Key query IDs:
- `8845758582119845` - Fetch post details
- Other IDs for comments, stories, user data

### GraphQL Request Example
```python
import requests

def fetch_post_data(shortcode):
    url = "https://www.instagram.com/graphql/query/"
    params = {
        'query_id': '8845758582119845',
        'variables': json.dumps({
            'shortcode': shortcode,
            'first': 50  # Number of comments
        })
    }

    headers = {
        'User-Agent': 'Mozilla/5.0...',
        'X-Requested-With': 'XMLHttpRequest'
    }

    response = requests.get(url, params=params, headers=headers)
    return response.json()
```

**Warning**: This approach requires:
- Residential proxies
- Frequent maintenance (Instagram updates frequently)
- Risk of blocks/bans

## Legal Considerations

### Terms of Service
- Automated browser extensions often violate ToS
- Using scraping while logged in can result in bans
- Public data scraping is generally legal
- Must comply with GDPR for personal data

### Best Practices
- Use official API when possible
- For third-party data, use reputable services
- Don't store unnecessary personal data
- Implement data retention policies

## Implementation Strategy

### For Personal Paraguay Analysis

1. **If you manage the account**: Use Instagram Graph API
2. **For public data**: Use Apify Instagram Comment Scraper
3. **Alternative**: Bright Data or custom GraphQL scraper

### Recommended Workflow
```python
# Using Apify (recommended for third-party accounts)
from apify_client import ApifyClient

def scrape_instagram_comments(post_urls):
    client = ApifyClient("YOUR_API_KEY")

    run_input = {
        "directUrls": post_urls,
        "resultsType": "comments",
        "resultsLimit": 1000
    }

    run = client.actor("apify/instagram-comment-scraper").call(run_input=run_input)

    comments = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        comments.append(item)

    return comments
```

## Data Schema

### Post Object
```json
{
  "id": "3012345678901234567",
  "shortcode": "CxYz123AbCd",
  "caption": "Activate tu plan con 50% OFF",
  "media_type": "IMAGE",
  "media_url": "https://instagram.com/...",
  "permalink": "https://www.instagram.com/p/CxYz123AbCd/",
  "timestamp": "2024-01-15T10:30:00+0000",
  "like_count": 2500,
  "comments_count": 156,
  "username": "personalpy"
}
```

### Comment Object
```json
{
  "id": "17895695668004550",
  "text": "Excelente servicio!",
  "timestamp": "2024-01-15T11:45:00.000Z",
  "username": "maria_gz",
  "user_id": "12345678901",
  "profile_pic_url": "https://...",
  "is_verified": false,
  "like_count": 8,
  "reply_count": 3,
  "replies": [
    {
      "id": "17895695668004551",
      "text": "Gracias!",
      "username": "personalpy"
    }
  ]
}
```

## Estimated Volume for Personal Paraguay
- **Followers**: ~110,000
- **Total Posts**: 2,497
- **Posts per month**: ~50-100 (typical for active business)
- **Comments per post**: 10-200 (varies by content type)
- **Reels engagement**: Higher (typically 2-5x more comments)
- **Total comments to process**: 500-10,000 per month
