# Comment Deduplication & Clustering Algorithms

## Overview
When analyzing thousands of comments, many will be similar or identical. Deduplication and clustering help identify common themes and reduce noise in analysis.

## Deduplication Approaches

### 1. Exact Match Deduplication
Simplest approach - remove identical comments.

```python
def exact_deduplicate(comments):
    seen = set()
    unique = []
    for comment in comments:
        normalized = comment['text'].strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            comment['duplicate_count'] = 1
            unique.append(comment)
        else:
            # Increment count for existing
            for c in unique:
                if c['text'].strip().lower() == normalized:
                    c['duplicate_count'] += 1
                    c['duplicates'].append(comment)
                    break
    return unique
```

### 2. Near-Duplicate Detection

#### Jaccard Similarity
Compare sets of words/n-grams.

```python
def jaccard_similarity(text1, text2):
    set1 = set(text1.lower().split())
    set2 = set(text2.lower().split())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0

# Example
text1 = "El servicio es muy malo"
text2 = "El servicio es malo"
# Jaccard = 4/5 = 0.8 (80% similar)
```

#### Shingling + MinHash (Scalable)
For large datasets, use Locality Sensitive Hashing.

```python
from datasketch import MinHash, MinHashLSH

def create_minhash(text, num_perm=128):
    minhash = MinHash(num_perm=num_perm)
    for word in text.lower().split():
        minhash.update(word.encode('utf8'))
    return minhash

def find_near_duplicates(comments, threshold=0.7):
    lsh = MinHashLSH(threshold=threshold, num_perm=128)

    # Index all comments
    minhashes = {}
    for i, comment in enumerate(comments):
        mh = create_minhash(comment['text'])
        minhashes[i] = mh
        lsh.insert(str(i), mh)

    # Find duplicates
    duplicate_groups = []
    processed = set()

    for i in range(len(comments)):
        if i in processed:
            continue
        similar = lsh.query(minhashes[i])
        if len(similar) > 1:
            group = [int(idx) for idx in similar]
            duplicate_groups.append(group)
            processed.update(group)

    return duplicate_groups
```

## Text Clustering Approaches

### 1. TF-IDF + K-Means

Classic approach for topic clustering.

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

def cluster_comments_tfidf(comments, n_clusters=10):
    texts = [c['text'] for c in comments]

    # Vectorize
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words='spanish',  # For Paraguay
        ngram_range=(1, 2)
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Cluster
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(tfidf_matrix)

    # Get cluster keywords
    feature_names = vectorizer.get_feature_names_out()
    cluster_keywords = {}

    for i in range(n_clusters):
        center = kmeans.cluster_centers_[i]
        top_indices = center.argsort()[-10:][::-1]
        keywords = [feature_names[idx] for idx in top_indices]
        cluster_keywords[i] = keywords

    # Assign clusters to comments
    for idx, comment in enumerate(comments):
        comment['cluster'] = int(clusters[idx])
        comment['cluster_keywords'] = cluster_keywords[clusters[idx]]

    return comments, cluster_keywords
```

### 2. Sentence Embeddings + DBSCAN

Better semantic understanding using transformers.

```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import numpy as np

def cluster_comments_embeddings(comments, eps=0.5, min_samples=3):
    texts = [c['text'] for c in comments]

    # Load multilingual model (important for Spanish/Guaraní)
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    # Generate embeddings
    embeddings = model.encode(texts, show_progress_bar=True)

    # Cluster with DBSCAN (doesn't require n_clusters)
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    clusters = clustering.fit_predict(embeddings)

    # Assign clusters
    for idx, comment in enumerate(comments):
        comment['cluster'] = int(clusters[idx])

    # Identify cluster representatives (closest to centroid)
    unique_clusters = set(clusters)
    representatives = {}

    for cluster_id in unique_clusters:
        if cluster_id == -1:  # Noise
            continue
        cluster_indices = np.where(clusters == cluster_id)[0]
        cluster_embeddings = embeddings[cluster_indices]
        centroid = np.mean(cluster_embeddings, axis=0)

        # Find closest to centroid
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        closest_idx = cluster_indices[np.argmin(distances)]
        representatives[cluster_id] = comments[closest_idx]['text']

    return comments, representatives
```

### 3. Topic Modeling with BERTopic

Advanced topic discovery.

```python
from bertopic import BERTopic

def discover_topics(comments):
    texts = [c['text'] for c in comments]

    # Create topic model
    topic_model = BERTopic(
        language="multilingual",
        calculate_probabilities=True,
        verbose=True
    )

    # Fit and transform
    topics, probs = topic_model.fit_transform(texts)

    # Assign topics to comments
    for idx, comment in enumerate(comments):
        comment['topic'] = int(topics[idx])
        comment['topic_probability'] = float(probs[idx].max())

    # Get topic information
    topic_info = topic_model.get_topic_info()

    return comments, topic_info, topic_model
```

## Grouping Similar Comments

### Implementation for Comment Condensation

```python
from collections import defaultdict
import numpy as np

class CommentCondenser:
    def __init__(self, similarity_threshold=0.8):
        self.threshold = similarity_threshold
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def condense(self, comments):
        if not comments:
            return []

        texts = [c['text'] for c in comments]
        embeddings = self.model.encode(texts)

        # Find similar groups
        groups = []
        assigned = set()

        for i in range(len(comments)):
            if i in assigned:
                continue

            # Start new group
            group = {
                'representative': comments[i],
                'similar_comments': [comments[i]],
                'authors': [comments[i].get('author', {})],
                'count': 1
            }

            # Find similar comments
            for j in range(i + 1, len(comments)):
                if j in assigned:
                    continue

                similarity = self._cosine_similarity(embeddings[i], embeddings[j])

                if similarity >= self.threshold:
                    group['similar_comments'].append(comments[j])
                    group['authors'].append(comments[j].get('author', {}))
                    group['count'] += 1
                    assigned.add(j)

            assigned.add(i)
            groups.append(group)

        # Sort by count (most common first)
        groups.sort(key=lambda x: x['count'], reverse=True)

        return groups

    def _cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

## Best Practices

### 1. Preprocessing
```python
import re
import unicodedata

def preprocess_comment(text):
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)

    # Lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r'http\S+|www\S+', '', text)

    # Remove mentions
    text = re.sub(r'@\w+', '', text)

    # Remove extra whitespace
    text = ' '.join(text.split())

    return text
```

### 2. Language Handling
Paraguay uses Spanish and Guaraní - use multilingual models:
- `paraphrase-multilingual-MiniLM-L12-v2`
- `sentence-transformers/LaBSE`
- `xlm-roberta-base`

### 3. Evaluation
```python
from sklearn.metrics import silhouette_score

def evaluate_clustering(embeddings, clusters):
    # Filter out noise (-1 cluster)
    mask = clusters != -1
    if sum(mask) < 2:
        return 0

    score = silhouette_score(embeddings[mask], clusters[mask])
    return score  # Range: -1 to 1, higher is better
```

## Output Structure

### Condensed Comment Group
```json
{
  "group_id": 1,
  "representative_text": "El servicio es muy malo, nunca funciona",
  "count": 45,
  "percentage": 12.5,
  "similar_comments": [
    {"text": "El servicio es malo", "author": "user1"},
    {"text": "Muy malo el servicio", "author": "user2"},
    {"text": "Servicio pésimo", "author": "user3"}
  ],
  "unique_authors": 42,
  "sentiment": "negative",
  "keywords": ["servicio", "malo", "funciona"],
  "platforms": {
    "facebook": 20,
    "instagram": 15,
    "twitter": 10
  },
  "date_range": {
    "earliest": "2024-01-01",
    "latest": "2024-01-31"
  }
}
```

## Recommended Algorithm Selection

| Use Case | Algorithm | Reason |
|----------|-----------|--------|
| Exact duplicates | Hash comparison | Fast, precise |
| Near duplicates | MinHash LSH | Scalable |
| Topic discovery | BERTopic | Automatic topic count |
| Fixed categories | TF-IDF + K-Means | Simple, interpretable |
| Semantic similarity | Sentence embeddings + DBSCAN | Best quality |

## Performance Considerations

### For < 10,000 comments
- Use sentence embeddings with cosine similarity
- No special optimization needed

### For 10,000 - 100,000 comments
- Use MinHash LSH for deduplication
- Batch embedding generation
- Consider FAISS for similarity search

### For > 100,000 comments
- Distributed processing (Spark, Dask)
- Approximate nearest neighbors (FAISS, Annoy)
- Incremental clustering
