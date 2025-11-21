# Commenter Analysis & Profiling

## Overview
Beyond comment content, analyzing commenter behavior provides valuable insights into customer segments, influencers, and engagement patterns.

## Data Points to Extract Per Commenter

### Identity
- User ID (platform-specific)
- Username/Handle
- Display Name
- Profile URL
- Verified status
- Profile picture URL

### Engagement Metrics
- Total comments on company posts
- Comment frequency (comments per month)
- Platforms they engage on
- Average likes received on comments
- Reply rate (do they respond to replies?)
- First interaction date
- Most recent interaction date

### Behavioral Patterns
- Time of day preferences
- Day of week preferences
- Post types they engage with
- Sentiment distribution of their comments
- Topics they discuss
- Response to company replies

## Commenter Classification

### 1. Engagement Level Classification

```python
class CommenterClassifier:
    def __init__(self):
        self.thresholds = {
            'super_fan': {'min_comments': 20, 'sentiment_positive': 0.7},
            'frequent_positive': {'min_comments': 10, 'sentiment_positive': 0.6},
            'frequent_negative': {'min_comments': 10, 'sentiment_negative': 0.6},
            'occasional': {'min_comments': 3},
            'one_time': {'max_comments': 2}
        }

    def classify(self, commenter_data):
        comment_count = commenter_data['total_comments']
        pos_ratio = commenter_data['sentiment_positive_ratio']
        neg_ratio = commenter_data['sentiment_negative_ratio']

        if (comment_count >= 20 and pos_ratio >= 0.7):
            return 'super_fan'
        elif (comment_count >= 10 and pos_ratio >= 0.6):
            return 'frequent_positive'
        elif (comment_count >= 10 and neg_ratio >= 0.6):
            return 'frequent_negative'
        elif comment_count >= 3:
            return 'occasional'
        else:
            return 'one_time'

    def get_classification_stats(self, all_commenters):
        classifications = {}
        for commenter in all_commenters:
            category = self.classify(commenter)
            if category not in classifications:
                classifications[category] = []
            classifications[category].append(commenter)

        return {
            category: {
                'count': len(commenters),
                'percentage': len(commenters) / len(all_commenters) * 100
            }
            for category, commenters in classifications.items()
        }
```

### 2. Influence Score Calculation

```python
def calculate_influence_score(commenter_data):
    """
    Calculate influence score based on multiple factors.
    Scale: 0-100
    """
    weights = {
        'verified': 20,
        'likes_received': 30,
        'comment_count': 20,
        'reply_engagement': 15,
        'recency': 15
    }

    score = 0

    # Verified status
    if commenter_data.get('is_verified', False):
        score += weights['verified']

    # Likes received (normalized)
    avg_likes = commenter_data.get('avg_likes_per_comment', 0)
    likes_score = min(avg_likes / 10 * weights['likes_received'], weights['likes_received'])
    score += likes_score

    # Comment frequency
    comment_count = commenter_data.get('total_comments', 0)
    comment_score = min(comment_count / 20 * weights['comment_count'], weights['comment_count'])
    score += comment_score

    # Reply engagement (replies received / comments made)
    reply_ratio = commenter_data.get('reply_ratio', 0)
    reply_score = min(reply_ratio * weights['reply_engagement'], weights['reply_engagement'])
    score += reply_score

    # Recency (active in last 30 days)
    days_since_last = commenter_data.get('days_since_last_comment', 365)
    if days_since_last <= 30:
        score += weights['recency']
    elif days_since_last <= 90:
        score += weights['recency'] * 0.5

    return round(score, 2)
```

### 3. Issue Reporter Identification

```python
def identify_issue_reporters(commenters, comments):
    """
    Identify users who frequently report specific issues.
    Valuable for identifying recurring problems.
    """
    issue_keywords = {
        'coverage': ['cobertura', 'señal', 'signal', 'red', 'network'],
        'billing': ['factura', 'cobro', 'pago', 'bill', 'charge'],
        'speed': ['lento', 'velocidad', 'slow', 'speed', 'mbps'],
        'service': ['atención', 'servicio', 'customer service'],
        'app': ['app', 'aplicación', 'application']
    }

    commenter_issues = {}

    for commenter in commenters:
        user_comments = [c for c in comments if c['author_id'] == commenter['id']]
        issue_counts = {issue: 0 for issue in issue_keywords}

        for comment in user_comments:
            text = comment['text'].lower()
            for issue, keywords in issue_keywords.items():
                if any(kw in text for kw in keywords):
                    issue_counts[issue] += 1

        commenter_issues[commenter['id']] = {
            'username': commenter['username'],
            'issues': issue_counts,
            'primary_issue': max(issue_counts, key=issue_counts.get) if any(issue_counts.values()) else None
        }

    return commenter_issues
```

## Aggregated Commenter Analytics

### Overall Statistics

```python
def calculate_commenter_statistics(commenters):
    """
    Calculate overall statistics about commenters.
    """
    total = len(commenters)

    return {
        'total_unique_commenters': total,
        'verified_users': sum(1 for c in commenters if c.get('is_verified', False)),
        'avg_comments_per_user': sum(c['total_comments'] for c in commenters) / total,
        'median_comments': sorted([c['total_comments'] for c in commenters])[total // 2],
        'top_10_percent_contribution': calculate_top_contribution(commenters, 0.1),
        'one_time_commenters': sum(1 for c in commenters if c['total_comments'] == 1),
        'return_rate': sum(1 for c in commenters if c['total_comments'] > 1) / total * 100
    }

def calculate_top_contribution(commenters, percentile):
    """
    Calculate what % of comments come from top X% of commenters.
    """
    sorted_commenters = sorted(commenters, key=lambda x: x['total_comments'], reverse=True)
    top_count = int(len(sorted_commenters) * percentile)
    top_commenters = sorted_commenters[:top_count]

    total_comments = sum(c['total_comments'] for c in commenters)
    top_comments = sum(c['total_comments'] for c in top_commenters)

    return top_comments / total_comments * 100
```

### Cross-Platform Analysis

```python
def analyze_cross_platform_engagement(commenters):
    """
    Identify users active across multiple platforms.
    """
    platform_combinations = {
        'facebook_only': 0,
        'instagram_only': 0,
        'twitter_only': 0,
        'multi_platform': 0
    }

    cross_platform_users = []

    for commenter in commenters:
        platforms = commenter.get('platforms', [])

        if len(platforms) > 1:
            platform_combinations['multi_platform'] += 1
            cross_platform_users.append({
                'username': commenter['username'],
                'platforms': platforms,
                'consistency': calculate_cross_platform_consistency(commenter)
            })
        elif 'facebook' in platforms:
            platform_combinations['facebook_only'] += 1
        elif 'instagram' in platforms:
            platform_combinations['instagram_only'] += 1
        elif 'twitter' in platforms:
            platform_combinations['twitter_only'] += 1

    return {
        'distribution': platform_combinations,
        'cross_platform_users': cross_platform_users
    }

def calculate_cross_platform_consistency(commenter):
    """
    Check if sentiment is consistent across platforms.
    """
    platform_sentiments = commenter.get('platform_sentiments', {})
    if len(platform_sentiments) < 2:
        return None

    sentiments = list(platform_sentiments.values())
    avg_sentiment = sum(sentiments) / len(sentiments)
    variance = sum((s - avg_sentiment) ** 2 for s in sentiments) / len(sentiments)

    return 'consistent' if variance < 0.1 else 'inconsistent'
```

### Time Pattern Analysis

```python
from collections import defaultdict
from datetime import datetime

def analyze_engagement_patterns(commenters, comments):
    """
    Analyze when users are most active.
    """
    hourly_activity = defaultdict(int)
    daily_activity = defaultdict(int)

    for comment in comments:
        timestamp = comment.get('timestamp')
        if not timestamp:
            continue

        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        hourly_activity[dt.hour] += 1
        daily_activity[dt.strftime('%A')] += 1

    # Find peak times
    peak_hour = max(hourly_activity, key=hourly_activity.get)
    peak_day = max(daily_activity, key=daily_activity.get)

    return {
        'hourly_distribution': dict(hourly_activity),
        'daily_distribution': dict(daily_activity),
        'peak_hour': peak_hour,
        'peak_day': peak_day,
        'recommendation': f"Post during {peak_hour}:00-{peak_hour+1}:00 on {peak_day}s"
    }
```

## Commenter Journey Tracking

```python
def track_commenter_journey(commenter_id, comments):
    """
    Track a commenter's journey over time.
    """
    user_comments = sorted(
        [c for c in comments if c['author_id'] == commenter_id],
        key=lambda x: x['timestamp']
    )

    if not user_comments:
        return None

    journey = {
        'first_contact': user_comments[0]['timestamp'],
        'first_sentiment': user_comments[0].get('sentiment', {}).get('label'),
        'latest_contact': user_comments[-1]['timestamp'],
        'latest_sentiment': user_comments[-1].get('sentiment', {}).get('label'),
        'total_interactions': len(user_comments),
        'sentiment_progression': [c.get('sentiment', {}).get('label') for c in user_comments],
        'topics_discussed': list(set(
            topic for c in user_comments
            for topic in c.get('topics', [])
        ))
    }

    # Calculate sentiment trend
    sentiment_scores = []
    for c in user_comments:
        if c.get('sentiment', {}).get('positive'):
            score = c['sentiment']['positive'] - c['sentiment'].get('negative', 0)
            sentiment_scores.append(score)

    if len(sentiment_scores) >= 3:
        first_half = sum(sentiment_scores[:len(sentiment_scores)//2]) / (len(sentiment_scores)//2)
        second_half = sum(sentiment_scores[len(sentiment_scores)//2:]) / (len(sentiment_scores) - len(sentiment_scores)//2)

        if second_half > first_half + 0.1:
            journey['sentiment_trend'] = 'improving'
        elif second_half < first_half - 0.1:
            journey['sentiment_trend'] = 'declining'
        else:
            journey['sentiment_trend'] = 'stable'

    return journey
```

## Output Schemas

### Individual Commenter Profile
```json
{
  "commenter_id": "user123",
  "username": "juan_perez",
  "display_name": "Juan Perez",
  "is_verified": false,
  "profile_url": "https://facebook.com/juan_perez",
  "platforms": ["facebook", "instagram"],
  "metrics": {
    "total_comments": 15,
    "avg_likes_per_comment": 3.5,
    "reply_ratio": 0.4,
    "comment_frequency": 2.5
  },
  "classification": "frequent_positive",
  "influence_score": 45.5,
  "sentiment_profile": {
    "positive_ratio": 0.65,
    "negative_ratio": 0.20,
    "neutral_ratio": 0.15
  },
  "top_topics": ["coverage", "service"],
  "engagement_pattern": {
    "preferred_hours": [19, 20, 21],
    "preferred_days": ["Saturday", "Sunday"]
  },
  "journey": {
    "first_contact": "2023-06-15",
    "sentiment_trend": "stable",
    "total_interactions": 15
  }
}
```

### Aggregated Commenter Report
```json
{
  "period": "2024-01",
  "total_unique_commenters": 3500,
  "classification_distribution": {
    "super_fan": {"count": 50, "percentage": 1.4},
    "frequent_positive": {"count": 200, "percentage": 5.7},
    "frequent_negative": {"count": 150, "percentage": 4.3},
    "occasional": {"count": 800, "percentage": 22.9},
    "one_time": {"count": 2300, "percentage": 65.7}
  },
  "top_contributors": [
    {"username": "maria_gz", "comments": 45, "sentiment": "positive"},
    {"username": "carlos99", "comments": 38, "sentiment": "negative"}
  ],
  "engagement_stats": {
    "avg_comments_per_user": 3.2,
    "return_rate": 34.3,
    "top_10_percent_contribution": 65.2
  },
  "cross_platform": {
    "multi_platform_users": 450,
    "percentage": 12.9
  },
  "peak_engagement": {
    "hour": 20,
    "day": "Friday"
  },
  "influencers": [
    {"username": "tech_reviewer", "influence_score": 85, "is_verified": true}
  ]
}
```

## Key Insights to Extract

### For Customer Service
1. **Frequent complainers** - Users who repeatedly report issues
2. **Unresolved issues** - Users with declining sentiment over time
3. **Cross-platform escalators** - Users who complain across multiple platforms

### For Marketing
1. **Brand advocates** - High-engagement, positive users
2. **Potential influencers** - Users with high like counts on comments
3. **Content preferences** - What types of posts specific users engage with

### For Product
1. **Feature requesters** - Users who mention specific features
2. **Regional issues** - Geographic patterns in complaints
3. **Competitor mentions** - Users who mention competitors
