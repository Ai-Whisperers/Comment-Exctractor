# Output Formats & Visualizations

## Overview
The social media comment extractor should produce multiple output formats to serve different use cases - from raw data for further analysis to executive summaries for quick insights.

## Output Categories

### 1. Raw Data Exports

#### JSON Export
Complete data with all fields preserved.

```json
{
  "export_metadata": {
    "generated_at": "2024-01-15T10:30:00Z",
    "company": "Personal Paraguay",
    "platforms": ["facebook", "instagram", "twitter"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-31"
    },
    "total_posts": 150,
    "total_comments": 8500
  },
  "posts": [...],
  "comments": [...],
  "commenters": [...],
  "analysis_results": {...}
}
```

#### CSV Export
Flat format for spreadsheet analysis.

**comments.csv**
```csv
comment_id,platform,post_id,text,author_id,author_username,timestamp,likes,replies,sentiment_label,sentiment_score,cluster_id
123456,facebook,789012,"Excelente servicio",user1,juan_perez,2024-01-15T10:30:00Z,5,2,POS,0.95,3
```

**commenters.csv**
```csv
commenter_id,username,platforms,total_comments,avg_likes,sentiment_positive_ratio,classification,influence_score
user1,juan_perez,"facebook,instagram",15,3.5,0.65,frequent_positive,45.5
```

#### Parquet Export
Efficient columnar format for big data tools.

```python
import pandas as pd

def export_to_parquet(comments_df, output_path):
    comments_df.to_parquet(
        output_path,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
```

### 2. Analytical Reports

#### Executive Summary (PDF/HTML)

```markdown
# Personal Paraguay - Social Media Analysis Report
## January 2024

### Key Metrics
- **Total Comments Analyzed**: 8,500
- **Unique Commenters**: 3,500
- **Overall Sentiment**: 35% Positive | 45% Negative | 20% Neutral

### Sentiment Trend
[Line chart showing sentiment over time]

### Top Issues
1. **Internet Speed** (1,200 mentions) - 85% negative
2. **Customer Service** (800 mentions) - 60% negative
3. **Billing** (600 mentions) - 70% negative

### Top Positive Themes
1. **Coverage Expansion** (400 mentions) - 90% positive
2. **New Plans** (300 mentions) - 75% positive

### Recommendations
1. Address internet speed issues in Asunción region
2. Improve customer service response times
3. Review billing transparency

### Detailed Analysis
[See appendix for complete data]
```

#### Comment Clusters Report

```json
{
  "clusters": [
    {
      "cluster_id": 1,
      "theme": "Internet Speed Complaints",
      "representative_comment": "El internet está muy lento, no puedo trabajar",
      "comment_count": 450,
      "percentage_of_total": 5.3,
      "sentiment": "negative",
      "sentiment_score": -0.85,
      "unique_authors": 380,
      "sample_comments": [
        "Internet lentísimo",
        "La velocidad es pésima",
        "No llega ni a 1 mbps"
      ],
      "keywords": ["lento", "velocidad", "internet", "mbps"],
      "platforms": {
        "facebook": 200,
        "twitter": 150,
        "instagram": 100
      },
      "peak_dates": ["2024-01-05", "2024-01-15"],
      "geographic_mentions": ["Asunción", "Luque", "Fernando de la Mora"]
    }
  ]
}
```

### 3. Visualizations

#### Dashboard Components

**1. Sentiment Distribution Pie Chart**
```python
import plotly.express as px

def sentiment_pie_chart(sentiment_data):
    fig = px.pie(
        values=[
            sentiment_data['positive'],
            sentiment_data['negative'],
            sentiment_data['neutral']
        ],
        names=['Positive', 'Negative', 'Neutral'],
        color_discrete_map={
            'Positive': '#28a745',
            'Negative': '#dc3545',
            'Neutral': '#6c757d'
        },
        title='Sentiment Distribution'
    )
    return fig
```

**2. Sentiment Timeline**
```python
import plotly.graph_objects as go

def sentiment_timeline(timeline_data):
    dates = list(timeline_data.keys())
    positive = [d['positive'] for d in timeline_data.values()]
    negative = [d['negative'] for d in timeline_data.values()]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=positive,
        name='Positive',
        line=dict(color='green')
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=negative,
        name='Negative',
        line=dict(color='red')
    ))

    fig.update_layout(
        title='Sentiment Over Time',
        xaxis_title='Date',
        yaxis_title='Comment Count'
    )
    return fig
```

**3. Word Cloud**
```python
from wordcloud import WordCloud
import matplotlib.pyplot as plt

def generate_wordcloud(texts, sentiment='all'):
    text = ' '.join(texts)

    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        colormap='RdYlGn' if sentiment == 'all' else ('Greens' if sentiment == 'positive' else 'Reds'),
        max_words=100
    ).generate(text)

    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    return plt
```

**4. Topic Distribution Bar Chart**
```python
def topic_bar_chart(topic_data):
    fig = px.bar(
        x=list(topic_data.keys()),
        y=list(topic_data.values()),
        color=list(topic_data.values()),
        color_continuous_scale='RdYlGn',
        title='Top Discussion Topics',
        labels={'x': 'Topic', 'y': 'Comment Count'}
    )
    return fig
```

**5. Commenter Engagement Heatmap**
```python
def engagement_heatmap(hourly_daily_data):
    fig = px.imshow(
        hourly_daily_data,
        labels=dict(x='Hour of Day', y='Day of Week', color='Comments'),
        x=list(range(24)),
        y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        color_continuous_scale='Blues',
        title='Engagement Heatmap'
    )
    return fig
```

**6. Platform Comparison**
```python
def platform_comparison(platform_data):
    fig = go.Figure(data=[
        go.Bar(name='Positive', x=platforms, y=[d['positive'] for d in platform_data.values()]),
        go.Bar(name='Negative', x=platforms, y=[d['negative'] for d in platform_data.values()]),
        go.Bar(name='Neutral', x=platforms, y=[d['neutral'] for d in platform_data.values()])
    ])
    fig.update_layout(barmode='group', title='Sentiment by Platform')
    return fig
```

### 4. Interactive Dashboard (Streamlit)

```python
import streamlit as st
import plotly.express as px

def create_dashboard(data):
    st.title("Personal Paraguay - Social Media Analysis")

    # Sidebar filters
    st.sidebar.header("Filters")
    platforms = st.sidebar.multiselect(
        "Platforms",
        options=["facebook", "instagram", "twitter"],
        default=["facebook", "instagram", "twitter"]
    )
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(data['start_date'], data['end_date'])
    )

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Comments", data['total_comments'])
    col2.metric("Positive %", f"{data['positive_pct']}%")
    col3.metric("Negative %", f"{data['negative_pct']}%")
    col4.metric("Unique Authors", data['unique_authors'])

    # Sentiment trend
    st.subheader("Sentiment Trend")
    st.plotly_chart(sentiment_timeline(data['timeline']))

    # Two columns for charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sentiment Distribution")
        st.plotly_chart(sentiment_pie_chart(data['sentiment']))

    with col2:
        st.subheader("Top Topics")
        st.plotly_chart(topic_bar_chart(data['topics']))

    # Clustered comments
    st.subheader("Top Comment Themes")
    for cluster in data['clusters'][:5]:
        with st.expander(f"{cluster['theme']} ({cluster['count']} comments)"):
            st.write(f"**Representative:** {cluster['representative']}")
            st.write(f"**Sentiment:** {cluster['sentiment']}")
            st.write("**Sample comments:**")
            for comment in cluster['samples']:
                st.write(f"- {comment}")

    # Commenter analysis
    st.subheader("Top Commenters")
    st.dataframe(data['top_commenters'])

    # Download buttons
    st.subheader("Export Data")
    col1, col2, col3 = st.columns(3)
    col1.download_button("Download CSV", data['csv'], "comments.csv")
    col2.download_button("Download JSON", data['json'], "analysis.json")
    col3.download_button("Download Report", data['pdf'], "report.pdf")
```

### 5. API Response Format

For integration with other systems.

```json
{
  "status": "success",
  "request_id": "req_123456",
  "data": {
    "summary": {
      "total_comments": 8500,
      "sentiment_distribution": {...},
      "date_range": {...}
    },
    "clusters": [...],
    "top_commenters": [...],
    "recommendations": [...]
  },
  "metadata": {
    "generated_at": "2024-01-15T10:30:00Z",
    "processing_time_ms": 15000,
    "api_version": "1.0"
  }
}
```

### 6. Alert/Notification Formats

For real-time monitoring.

```json
{
  "alert_type": "sentiment_spike",
  "severity": "high",
  "timestamp": "2024-01-15T10:30:00Z",
  "message": "Negative sentiment increased 50% in last 2 hours",
  "details": {
    "current_negative_pct": 75,
    "baseline_negative_pct": 50,
    "top_issues": ["internet_speed", "outage"],
    "sample_comments": [...]
  },
  "recommended_action": "Investigate potential service outage"
}
```

## Output Delivery Methods

### 1. File Storage
- Local filesystem
- Cloud storage (S3, GCS, Azure Blob)
- FTP/SFTP

### 2. Database
- PostgreSQL for structured data
- MongoDB for flexible documents
- Elasticsearch for search/analytics

### 3. Real-time
- Webhooks
- WebSocket streaming
- Message queues (Kafka, RabbitMQ)

### 4. Email Reports
- Daily/weekly digest
- Alerts on thresholds
- Executive summaries

### 5. Integrations
- Slack/Teams notifications
- CRM integration (Salesforce, HubSpot)
- BI tools (Tableau, PowerBI, Looker)

## Complete Output Package

For each analysis run, generate:

```
output/
├── raw/
│   ├── comments.json
│   ├── comments.csv
│   ├── commenters.json
│   └── posts.json
├── analysis/
│   ├── sentiment_analysis.json
│   ├── clusters.json
│   ├── commenter_profiles.json
│   └── topic_analysis.json
├── reports/
│   ├── executive_summary.pdf
│   ├── detailed_report.html
│   └── recommendations.md
├── visualizations/
│   ├── sentiment_pie.png
│   ├── sentiment_timeline.png
│   ├── wordcloud.png
│   ├── topic_bars.png
│   └── engagement_heatmap.png
└── dashboard/
    └── interactive_dashboard.html
```
