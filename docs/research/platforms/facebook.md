# Facebook Data Extraction Research

## Overview
Facebook is one of the largest social media platforms with extensive business page features. For Personal Paraguay, their page has **495,428 likes** and approximately **3,080 people talking about it**.

## Official API: Graph API

### Endpoints Available

#### Page Posts
```
GET /{page-id}/posts
```
Returns posts published by a Page.

#### Post Comments
```
GET /{page-post-id}/comments
```
Returns comments on a specific post.

Reference: https://developers.facebook.com/docs/graph-api/reference/page-post/comments/

### Authentication Requirements
- **App Access Token** or **Page Access Token**
- Required permissions:
  - `pages_read_engagement`
  - `pages_read_user_content`
  - `pages_show_list`

### Data Available

#### Post Data
- `id` - Post identifier
- `message` - Post text content
- `created_time` - Timestamp
- `shares` - Share count
- `reactions` - Like, love, haha, wow, sad, angry counts
- `comments` - Comment summary
- `attachments` - Media (images, videos, links)
- `permalink_url` - Direct link to post

#### Comment Data
- `id` - Comment identifier
- `message` - Comment text
- `created_time` - Timestamp
- `from` - Commenter info (id, name)
- `like_count` - Number of likes
- `comment_count` - Number of replies
- `parent` - Parent comment (for nested replies)
- `attachment` - Media attachments

### Rate Limits
- 200 calls per user per hour
- 4800 calls per app per 24 hours for pages
- Pagination required for large datasets

### Limitations
- Only accessible for pages you manage (with page access token)
- Third-party page scraping requires special permissions
- Some user data may be anonymized for privacy

## Third-Party Solutions

### Apify Facebook Scraper
- **Cost**: ~$1.50 per 1,000 posts
- **Features**: No authentication needed, works on public pages
- **Data**: Posts, comments, reactions, shares

### Bright Data
- **Features**: Residential proxy network
- **Cost**: Usage-based pricing
- **Reliability**: High, with proxy rotation

### Custom Scraping
- Requires residential proxies
- Must handle frequent site updates
- Risk of IP bans

## Legal Considerations

### Terms of Service
- Public data scraping is generally legal
- Must comply with GDPR/CCPA for personal data
- Cannot use for harassment or spam
- Commercial use requires careful review

### Best Practices
- Respect rate limits
- Don't collect private information
- Store data securely
- Provide opt-out mechanisms

## Implementation Approach

### Recommended Strategy
1. **Primary**: Use Graph API with proper authentication
2. **Fallback**: Apify for public page data
3. **Custom**: Build scraper with residential proxies

### Code Example (Graph API)
```python
import requests

def get_page_posts(page_id, access_token):
    url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
    params = {
        'access_token': access_token,
        'fields': 'id,message,created_time,shares,reactions.summary(true),comments.summary(true)',
        'limit': 100
    }

    posts = []
    while url:
        response = requests.get(url, params=params)
        data = response.json()
        posts.extend(data.get('data', []))
        url = data.get('paging', {}).get('next')
        params = {}  # Next URL includes params

    return posts

def get_post_comments(post_id, access_token):
    url = f"https://graph.facebook.com/v18.0/{post_id}/comments"
    params = {
        'access_token': access_token,
        'fields': 'id,message,created_time,from,like_count,comment_count,parent',
        'limit': 100
    }

    comments = []
    while url:
        response = requests.get(url, params=params)
        data = response.json()
        comments.extend(data.get('data', []))
        url = data.get('paging', {}).get('next')
        params = {}

    return comments
```

## Data Schema

### Post Object
```json
{
  "id": "123456789_987654321",
  "message": "Check out our new plan!",
  "created_time": "2024-01-15T10:30:00+0000",
  "shares": {"count": 150},
  "reactions": {
    "summary": {"total_count": 1200}
  },
  "comments": {
    "summary": {"total_count": 89}
  },
  "permalink_url": "https://www.facebook.com/personalpy/posts/987654321"
}
```

### Comment Object
```json
{
  "id": "987654321_111222333",
  "message": "Great service!",
  "created_time": "2024-01-15T11:45:00+0000",
  "from": {
    "id": "444555666",
    "name": "Juan Perez"
  },
  "like_count": 5,
  "comment_count": 2
}
```

## Estimated Volume for Personal Paraguay
- **Page Likes**: ~495,000
- **Posts per month**: ~30-60 (typical for telecom)
- **Comments per post**: 20-500 (varies by engagement)
- **Total comments to process**: 1,000-30,000 per month
