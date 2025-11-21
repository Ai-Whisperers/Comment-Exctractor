# Twitter/X Data Extraction Research

## Overview
Twitter (now X) remains important for customer service and real-time engagement. Personal Paraguay likely uses @personalpy handle (consistent with other platforms).

## Official API: Twitter API v2

### Endpoints Available

#### User Tweets
```
GET /2/users/{id}/tweets
```
Returns tweets from a specific user.

#### Tweet Replies (Search)
```
GET /2/tweets/search/recent
```
Search for tweets replying to a specific tweet using `conversation_id`.

### Key Feature: conversation_id
In API v2, every tweet has a `conversation_id` that threads all replies together, making it easier to reconstruct reply chains.

```python
# Find all replies to a tweet
GET /2/tweets/search/recent?query=conversation_id:1234567890
```

### Authentication Requirements
- **Bearer Token** (App-only auth)
- **OAuth 2.0** (User context)
- API Key and Secret

### API Tiers (as of 2024)
| Tier | Price | Tweet Cap | Features |
|------|-------|-----------|----------|
| Free | $0 | 1,500/month | Basic write |
| Basic | $100/month | 10,000/month | Read + write |
| Pro | $5,000/month | 1M/month | Full access |
| Enterprise | Custom | Unlimited | All features |

### Data Available

#### Tweet Data
- `id` - Tweet identifier
- `text` - Tweet content
- `created_at` - Timestamp
- `author_id` - User who posted
- `conversation_id` - Thread identifier
- `public_metrics` - Retweets, replies, likes, quotes
- `attachments` - Media, polls
- `entities` - Mentions, hashtags, URLs

#### Reply Data
Same structure as tweets, with additional:
- `in_reply_to_user_id` - User being replied to
- `referenced_tweets` - Parent tweet info

### Limitations

1. **Rate Limits**: Strict, varies by tier
2. **Recent Only**: Free/Basic tiers only access recent tweets (7 days)
3. **High-Volume Accounts**: Cannot reconstruct all replies for accounts like NYT due to volume
4. **Cost**: Full access is expensive ($5,000+/month)

## Third-Party Solutions

### Apify Twitter Scrapers

#### Twitter Comment Scraper
- **Cost**: $0.20 per 1,000 replies
- **No auth needed**
- **Features**: Extract all replies including hidden/spam

```python
# Data structure
{
    "tweet_id": "1234567890123456789",
    "text": "Great service!",
    "created_at": "2024-01-15T10:30:00.000Z",
    "author": {
        "id": "987654321",
        "username": "user123",
        "name": "User Name",
        "followers_count": 500
    },
    "public_metrics": {
        "like_count": 5,
        "reply_count": 2,
        "retweet_count": 1
    }
}
```

#### Full Reply Scraper
- Captures hidden and nested replies
- Includes sentiment and tone analysis
- No cookies required

### ScrapingDog Twitter API
- Extract views, retweets, likes, bookmarks
- Per-request pricing
- Good for market research

### Octoparse (No-Code)
- Visual scraper builder
- Unlimited extraction
- Includes: tweets, user info, likes, retweets, comments, followers

## Implementation Approach

### Using Official API v2
```python
import requests

class TwitterClient:
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"

    def get_user_tweets(self, user_id, max_results=100):
        url = f"{self.base_url}/users/{user_id}/tweets"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,conversation_id",
            "expansions": "author_id"
        }

        response = requests.get(url, headers=headers, params=params)
        return response.json()

    def get_tweet_replies(self, conversation_id):
        url = f"{self.base_url}/tweets/search/recent"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "query": f"conversation_id:{conversation_id}",
            "tweet.fields": "created_at,public_metrics,in_reply_to_user_id",
            "expansions": "author_id",
            "max_results": 100
        }

        response = requests.get(url, headers=headers, params=params)
        return response.json()
```

### Using Apify (Third-Party)
```python
from apify_client import ApifyClient

def scrape_tweet_replies(tweet_urls):
    client = ApifyClient("YOUR_API_KEY")

    run_input = {
        "startUrls": [{"url": url} for url in tweet_urls],
        "maxItems": 1000
    }

    run = client.actor("muhammetakkurtt/twitter-x-comment-scraper").call(run_input=run_input)

    replies = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        replies.append(item)

    return replies
```

## Legal Considerations

### Terms of Service
- Scraping public data is generally legal
- Must follow Twitter Developer Policy
- Cannot use for spam or harassment
- Be mindful of copyright on content

### API Terms
- Cannot redistribute bulk data
- Must display tweets with proper formatting
- Cannot modify tweet content
- Must include attribution

## Data Schema

### Tweet Object
```json
{
  "id": "1234567890123456789",
  "text": "Conoce nuestros nuevos planes! #PersonalPy",
  "created_at": "2024-01-15T10:30:00.000Z",
  "author_id": "123456789",
  "conversation_id": "1234567890123456789",
  "public_metrics": {
    "retweet_count": 50,
    "reply_count": 89,
    "like_count": 320,
    "quote_count": 15,
    "impression_count": 15000
  },
  "entities": {
    "hashtags": [{"tag": "PersonalPy"}],
    "mentions": []
  }
}
```

### Reply Object
```json
{
  "id": "1234567890123456790",
  "text": "@personalpy excelente!",
  "created_at": "2024-01-15T11:45:00.000Z",
  "author_id": "987654321",
  "conversation_id": "1234567890123456789",
  "in_reply_to_user_id": "123456789",
  "public_metrics": {
    "like_count": 5,
    "reply_count": 1
  },
  "author": {
    "id": "987654321",
    "username": "user123",
    "name": "Juan Perez",
    "verified": false
  }
}
```

## Estimated Volume for Personal Paraguay
- **Typical posts/month**: 30-100 (customer service focus)
- **Replies per tweet**: 5-100 (varies by topic)
- **Customer service mentions**: 50-500/month
- **Total comments to process**: 500-5,000 per month

## Special Considerations

### Customer Service Focus
Telecom companies heavily use Twitter for:
- Customer complaints
- Technical support
- Service outages
- Billing questions

This means:
- Higher reply volumes on problem posts
- Many mentions (not direct replies)
- Rapid response expectation
- Sentiment often skews negative (complaints)
