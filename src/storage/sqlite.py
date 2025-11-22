"""SQLite storage implementation."""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set

from ..core.models import (
    Comment,
    Post,
    Profile,
    Author,
    Platform,
    ExtractionStats,
)
from ..core.exceptions import StorageError, ValidationError
from ..config.paths import get_paths

logger = logging.getLogger(__name__)


__all__ = ["SQLiteStorage"]


class SQLiteStorage:
    """SQLite storage backend for comments, posts, and profiles."""

    def __init__(self, db_path: str = None):
        """
        Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file (uses centralized config if None)

        Raises:
            ValidationError: If db_path contains path traversal attempts
        """
        if db_path is None:
            self.db_path = get_paths().database_path
        else:
            # Check for path traversal
            if '..' in str(db_path):
                raise ValidationError(
                    "Invalid database path: contains path traversal",
                    field="db_path"
                )
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Comments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    platform_id TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    author_id TEXT,
                    author_username TEXT,
                    author_display_name TEXT,
                    author_profile_url TEXT,
                    author_is_verified BOOLEAN DEFAULT FALSE,
                    published_at TIMESTAMP,
                    likes INTEGER DEFAULT 0,
                    replies_count INTEGER DEFAULT 0,
                    parent_id TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, platform_id)
                )
            """)

            # Posts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    platform_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    url TEXT,
                    text TEXT,
                    published_at TIMESTAMP,
                    likes INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    media_type TEXT,
                    media_urls TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, platform_id)
                )
            """)

            # Profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    platform_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    description TEXT,
                    url TEXT,
                    profile_image TEXT,
                    cover_image TEXT,
                    followers_count INTEGER DEFAULT 0,
                    following_count INTEGER DEFAULT 0,
                    posts_count INTEGER DEFAULT 0,
                    is_verified BOOLEAN DEFAULT FALSE,
                    raw_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, platform_id)
                )
            """)

            # Extraction history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extraction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    posts_scraped INTEGER DEFAULT 0,
                    comments_found INTEGER DEFAULT 0,
                    new_comments_saved INTEGER DEFAULT 0,
                    duplicates_skipped INTEGER DEFAULT 0,
                    last_post_date TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error TEXT,
                    UNIQUE(client, platform, account_id)
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_comments_client_platform
                ON comments(client, platform)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_comments_post_id
                ON comments(post_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_comments_published_at
                ON comments(published_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_client_platform
                ON posts(client, platform)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_published_at
                ON posts(published_at)
            """)

            conn.commit()
            logger.info(f"Initialized database at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def save_comment(self, client: str, comment: Comment) -> bool:
        """
        Save a comment to the database.

        Args:
            client: Client name
            comment: Comment to save

        Returns:
            True if new comment saved, False if duplicate
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR IGNORE INTO comments (
                        client, platform, platform_id, post_id, text,
                        author_id, author_username, author_display_name,
                        author_profile_url, author_is_verified,
                        published_at, likes, replies_count, parent_id, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client,
                    comment.platform.value,
                    comment.platform_id,
                    comment.post_id,
                    comment.text,
                    comment.author.platform_id,
                    comment.author.username,
                    comment.author.display_name,
                    comment.author.profile_url,
                    comment.author.is_verified,
                    comment.published_at.isoformat() if comment.published_at else None,
                    comment.likes,
                    comment.replies_count,
                    comment.parent_id,
                    json.dumps(comment.raw_data) if comment.raw_data else None
                ))

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.IntegrityError as e:
            # Duplicate entry - this is expected, not an error
            logger.debug(f"Comment already exists: {comment.platform_id}")
            return False
        except sqlite3.Error as e:
            raise StorageError(
                f"Database error saving comment: {e}",
                operation="save_comment",
                original_error=e
            )

    def save_post(self, client: str, post: Post) -> bool:
        """
        Save a post to the database.

        Args:
            client: Client name
            post: Post to save

        Returns:
            True if new post saved, False if duplicate
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR IGNORE INTO posts (
                        client, platform, platform_id, account_id, url, text,
                        published_at, likes, comments_count, shares,
                        media_type, media_urls, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client,
                    post.platform.value,
                    post.platform_id,
                    post.account_id,
                    post.url,
                    post.text,
                    post.published_at.isoformat() if post.published_at else None,
                    post.likes,
                    post.comments_count,
                    post.shares,
                    post.media_type,
                    json.dumps(post.media_urls) if post.media_urls else None,
                    json.dumps(post.raw_data) if post.raw_data else None
                ))

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.IntegrityError as e:
            logger.debug(f"Post already exists: {post.platform_id}")
            return False
        except sqlite3.Error as e:
            raise StorageError(
                f"Database error saving post: {e}",
                operation="save_post",
                original_error=e
            )

    def save_profile(self, client: str, profile: Profile) -> bool:
        """
        Save or update a profile.

        Args:
            client: Client name
            profile: Profile to save

        Returns:
            True if saved/updated
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO profiles (
                        client, platform, platform_id, username, display_name,
                        description, url, profile_image, cover_image,
                        followers_count, following_count, posts_count,
                        is_verified, raw_data, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client,
                    profile.platform.value,
                    profile.platform_id,
                    profile.username,
                    profile.display_name,
                    profile.description,
                    profile.url,
                    profile.profile_image,
                    profile.cover_image,
                    profile.followers_count,
                    profile.following_count,
                    profile.posts_count,
                    profile.is_verified,
                    json.dumps(profile.raw_data) if profile.raw_data else None,
                    datetime.now(timezone.utc).isoformat()
                ))

                conn.commit()
                return True

        except sqlite3.Error as e:
            raise StorageError(
                f"Database error saving profile: {e}",
                operation="save_profile",
                original_error=e
            )

    def get_comments(
        self,
        client: str,
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Comment]:
        """
        Get comments from storage.

        Args:
            client: Client name
            platform: Filter by platform
            since: Comments after this date
            until: Comments before this date
            limit: Maximum number to return

        Returns:
            List of comments
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM comments WHERE client = ?"
                params = [client]

                if platform:
                    query += " AND platform = ?"
                    params.append(platform)

                if since:
                    query += " AND published_at >= ?"
                    params.append(since.isoformat())

                if until:
                    query += " AND published_at <= ?"
                    params.append(until.isoformat())

                query += " ORDER BY published_at DESC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [self._row_to_comment(row) for row in rows]

        except sqlite3.Error as e:
            raise StorageError(
                f"Database error getting comments: {e}",
                operation="get_comments",
                original_error=e
            )

    def get_posts(
        self,
        client: str,
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Post]:
        """
        Get posts from storage.

        Args:
            client: Client name
            platform: Filter by platform
            since: Posts after this date
            until: Posts before this date

        Returns:
            List of posts
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM posts WHERE client = ?"
                params = [client]

                if platform:
                    query += " AND platform = ?"
                    params.append(platform)

                if since:
                    query += " AND published_at >= ?"
                    params.append(since.isoformat())

                if until:
                    query += " AND published_at <= ?"
                    params.append(until.isoformat())

                query += " ORDER BY published_at DESC"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [self._row_to_post(row) for row in rows]

        except sqlite3.Error as e:
            raise StorageError(
                f"Database error getting posts: {e}",
                operation="get_posts",
                original_error=e
            )

    def get_last_extraction_date(
        self,
        client: str,
        platform: str,
        account_id: str
    ) -> Optional[datetime]:
        """
        Get the date of the last extraction.

        Args:
            client: Client name
            platform: Platform name
            account_id: Account identifier

        Returns:
            Last extraction date or None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT last_post_date FROM extraction_history
                    WHERE client = ? AND platform = ? AND account_id = ?
                """, (client, platform, account_id))

                row = cursor.fetchone()
                if row and row["last_post_date"]:
                    return datetime.fromisoformat(row["last_post_date"])

                return None

        except sqlite3.Error as e:
            logger.warning(f"Database error getting last extraction date: {e}")
            return None

    def update_extraction_history(
        self,
        client: str,
        platform: str,
        account_id: str,
        stats: ExtractionStats
    ) -> None:
        """
        Update extraction history.

        Args:
            client: Client name
            platform: Platform name
            account_id: Account identifier
            stats: Extraction statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get the latest post date from the extracted posts
                cursor.execute("""
                    SELECT MAX(published_at) as latest FROM posts
                    WHERE client = ? AND platform = ? AND account_id = ?
                """, (client, platform, account_id))

                row = cursor.fetchone()
                last_post_date = row["latest"] if row else None

                cursor.execute("""
                    INSERT OR REPLACE INTO extraction_history (
                        client, platform, account_id, posts_scraped,
                        comments_found, new_comments_saved, duplicates_skipped,
                        last_post_date, started_at, completed_at, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client,
                    platform,
                    account_id,
                    stats.posts_scraped,
                    stats.comments_found,
                    stats.new_comments_saved,
                    stats.duplicates_skipped,
                    last_post_date,
                    stats.started_at.isoformat(),
                    stats.completed_at.isoformat() if stats.completed_at else None,
                    stats.error
                ))

                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Database error updating extraction history: {e}")

    def get_comment_count(
        self,
        client: str,
        platform: Optional[str] = None
    ) -> int:
        """
        Get total comment count.

        Args:
            client: Client name
            platform: Optional platform filter

        Returns:
            Number of comments
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if platform:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM comments
                        WHERE client = ? AND platform = ?
                    """, (client, platform))
                else:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM comments
                        WHERE client = ?
                    """, (client,))

                row = cursor.fetchone()
                return row["count"] if row else 0

        except sqlite3.Error as e:
            logger.error(f"Database error getting comment count: {e}")
            return 0

    def get_post_comment_count(
        self,
        client: str,
        post_id: str
    ) -> int:
        """
        Get comment count for a specific post.

        Args:
            client: Client name
            post_id: Post platform ID

        Returns:
            Number of comments for this post
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count FROM comments
                    WHERE client = ? AND post_id = ?
                """, (client, post_id))
                row = cursor.fetchone()
                return row["count"] if row else 0

        except sqlite3.Error as e:
            logger.error(f"Database error getting post comment count: {e}")
            return 0

    def get_posts_with_comments_set(
        self,
        client: str,
        platform: str
    ) -> set:
        """
        Get set of post IDs that already have comments.

        Args:
            client: Client name
            platform: Platform name

        Returns:
            Set of post_ids that have at least one comment
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT post_id FROM comments
                    WHERE client = ? AND platform = ?
                """, (client, platform))
                return {row["post_id"] for row in cursor.fetchall()}

        except sqlite3.Error as e:
            logger.error(f"Database error getting posts with comments: {e}")
            return set()

    def get_duplicate_comments(
        self,
        client: str,
        platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find duplicate comments (same text appearing multiple times).

        Args:
            client: Client name
            platform: Optional platform filter

        Returns:
            List of duplicate comment groups
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if platform:
                    cursor.execute("""
                        SELECT text, COUNT(*) as count, GROUP_CONCAT(platform_id) as ids
                        FROM comments
                        WHERE client = ? AND platform = ?
                        GROUP BY text
                        HAVING count > 1
                        ORDER BY count DESC
                    """, (client, platform))
                else:
                    cursor.execute("""
                        SELECT text, COUNT(*) as count, GROUP_CONCAT(platform_id) as ids
                        FROM comments
                        WHERE client = ?
                        GROUP BY text
                        HAVING count > 1
                        ORDER BY count DESC
                    """, (client,))

                rows = cursor.fetchall()
                return [
                    {
                        "text": row["text"][:100] + "..." if len(row["text"]) > 100 else row["text"],
                        "count": row["count"],
                        "ids": row["ids"].split(",") if row["ids"] else []
                    }
                    for row in rows
                ]

        except sqlite3.Error as e:
            logger.error(f"Database error getting duplicate comments: {e}")
            return []

    def get_duplicate_count(
        self,
        client: str,
        platform: Optional[str] = None
    ) -> int:
        """
        Get count of duplicate comments.

        Args:
            client: Client name
            platform: Optional platform filter

        Returns:
            Number of duplicate comment entries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if platform:
                    cursor.execute("""
                        SELECT SUM(count - 1) as duplicates FROM (
                            SELECT COUNT(*) as count
                            FROM comments
                            WHERE client = ? AND platform = ?
                            GROUP BY text
                            HAVING count > 1
                        )
                    """, (client, platform))
                else:
                    cursor.execute("""
                        SELECT SUM(count - 1) as duplicates FROM (
                            SELECT COUNT(*) as count
                            FROM comments
                            WHERE client = ?
                            GROUP BY text
                            HAVING count > 1
                        )
                    """, (client,))

                row = cursor.fetchone()
                return row["duplicates"] if row and row["duplicates"] else 0

        except sqlite3.Error as e:
            logger.error(f"Database error getting duplicate count: {e}")
            return 0

    def remove_duplicate_comments(
        self,
        client: str,
        platform: Optional[str] = None
    ) -> int:
        """
        Remove duplicate comments, keeping only the first occurrence.

        Args:
            client: Client name
            platform: Optional platform filter

        Returns:
            Number of duplicates removed
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if platform:
                    cursor.execute("""
                        DELETE FROM comments
                        WHERE id NOT IN (
                            SELECT MIN(id)
                            FROM comments
                            WHERE client = ? AND platform = ?
                            GROUP BY text
                        )
                        AND client = ? AND platform = ?
                    """, (client, platform, client, platform))
                else:
                    cursor.execute("""
                        DELETE FROM comments
                        WHERE id NOT IN (
                            SELECT MIN(id)
                            FROM comments
                            WHERE client = ?
                            GROUP BY text
                        )
                        AND client = ?
                    """, (client, client))

                removed = cursor.rowcount
                conn.commit()
                logger.info(f"Removed {removed} duplicate comments for client={client}")
                return removed

        except sqlite3.Error as e:
            logger.error(f"Database error removing duplicates: {e}")
            return 0

    def _row_to_comment(self, row: sqlite3.Row) -> Comment:
        """Convert database row to Comment model."""
        return Comment(
            platform=Platform(row["platform"]),
            platform_id=row["platform_id"],
            post_id=row["post_id"],
            text=row["text"],
            author=Author(
                platform_id=row["author_id"],
                username=row["author_username"],
                display_name=row["author_display_name"],
                profile_url=row["author_profile_url"],
                is_verified=bool(row["author_is_verified"]),
            ),
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            likes=row["likes"],
            replies_count=row["replies_count"],
            parent_id=row["parent_id"],
            raw_data=json.loads(row["raw_data"]) if row["raw_data"] else {}
        )

    def _row_to_post(self, row: sqlite3.Row) -> Post:
        """Convert database row to Post model."""
        return Post(
            platform=Platform(row["platform"]),
            platform_id=row["platform_id"],
            account_id=row["account_id"],
            url=row["url"],
            text=row["text"],
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            likes=row["likes"],
            comments_count=row["comments_count"],
            shares=row["shares"],
            media_type=row["media_type"],
            media_urls=json.loads(row["media_urls"]) if row["media_urls"] else [],
            raw_data=json.loads(row["raw_data"]) if row["raw_data"] else {}
        )

    # Batch save methods for StorageBackend compatibility

    def save_comments_batch(
        self,
        client: str,
        comments: List[Comment],
        batch_size: int = 500
    ) -> Tuple[int, int]:
        """
        Save multiple comments using batch insert for better performance.

        Args:
            client: Client name
            comments: List of comments to save
            batch_size: Number of comments to insert per batch

        Returns:
            Tuple of (saved_count, duplicate_count)
        """
        if not comments:
            return 0, 0

        total_saved = 0
        total_duplicates = 0

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Process in batches
                for i in range(0, len(comments), batch_size):
                    batch = comments[i:i + batch_size]

                    # Prepare batch data
                    batch_data = [
                        (
                            client,
                            comment.platform.value,
                            comment.platform_id,
                            comment.post_id,
                            comment.text,
                            comment.author.platform_id,
                            comment.author.username,
                            comment.author.display_name,
                            comment.author.profile_url,
                            comment.author.is_verified,
                            comment.published_at.isoformat() if comment.published_at else None,
                            comment.likes,
                            comment.replies_count,
                            comment.parent_id,
                            json.dumps(comment.raw_data) if comment.raw_data else None
                        )
                        for comment in batch
                    ]

                    # Execute batch insert
                    cursor.executemany("""
                        INSERT OR IGNORE INTO comments (
                            client, platform, platform_id, post_id, text,
                            author_id, author_username, author_display_name,
                            author_profile_url, author_is_verified,
                            published_at, likes, replies_count, parent_id, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch_data)

                    batch_saved = cursor.rowcount
                    total_saved += batch_saved
                    total_duplicates += len(batch) - batch_saved

                conn.commit()

            logger.info(
                f"Batch saved {total_saved} comments for {client} "
                f"({total_duplicates} duplicates skipped)"
            )
            return total_saved, total_duplicates

        except sqlite3.Error as e:
            raise StorageError(
                f"Database error in batch save: {e}",
                operation="save_comments_batch",
                original_error=e
            )

    def save_posts_batch(
        self,
        client: str,
        posts: List[Post],
        batch_size: int = 500
    ) -> Tuple[int, int]:
        """
        Save multiple posts using batch insert for better performance.

        Args:
            client: Client name
            posts: List of posts to save
            batch_size: Number of posts to insert per batch

        Returns:
            Tuple of (saved_count, duplicate_count)
        """
        if not posts:
            return 0, 0

        total_saved = 0
        total_duplicates = 0

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Process in batches
                for i in range(0, len(posts), batch_size):
                    batch = posts[i:i + batch_size]

                    # Prepare batch data
                    batch_data = [
                        (
                            client,
                            post.platform.value,
                            post.platform_id,
                            post.account_id,
                            post.url,
                            post.text,
                            post.published_at.isoformat() if post.published_at else None,
                            post.likes,
                            post.comments_count,
                            post.shares,
                            post.media_type,
                            json.dumps(post.media_urls) if post.media_urls else None,
                            json.dumps(post.raw_data) if post.raw_data else None
                        )
                        for post in batch
                    ]

                    # Execute batch insert
                    cursor.executemany("""
                        INSERT OR IGNORE INTO posts (
                            client, platform, platform_id, account_id, url, text,
                            published_at, likes, comments_count, shares,
                            media_type, media_urls, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch_data)

                    batch_saved = cursor.rowcount
                    total_saved += batch_saved
                    total_duplicates += len(batch) - batch_saved

                conn.commit()

            logger.info(
                f"Batch saved {total_saved} posts for {client} "
                f"({total_duplicates} duplicates skipped)"
            )
            return total_saved, total_duplicates

        except sqlite3.Error as e:
            raise StorageError(
                f"Database error in batch save: {e}",
                operation="save_posts_batch",
                original_error=e
            )

    def exists_comment(self, platform: str, platform_id: str) -> bool:
        """
        Check if a comment exists in the database.

        Args:
            platform: Platform name
            platform_id: Platform-specific comment ID

        Returns:
            True if comment exists
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM comments
                    WHERE platform = ? AND platform_id = ?
                    LIMIT 1
                """, (platform, platform_id))
                return cursor.fetchone() is not None
        except sqlite3.Error:
            return False

    def exists_comments_batch(
        self,
        platform: str,
        platform_ids: List[str]
    ) -> Dict[str, bool]:
        """
        Check if multiple comments exist in the database.

        More efficient than calling exists_comment for each ID.

        Args:
            platform: Platform name
            platform_ids: List of platform-specific comment IDs

        Returns:
            Dictionary mapping platform_id to exists (True/False)
        """
        if not platform_ids:
            return {}

        result = {pid: False for pid in platform_ids}

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # SQLite has a limit on number of placeholders (~999),
                # so we batch the queries
                batch_size = 500
                for i in range(0, len(platform_ids), batch_size):
                    batch = platform_ids[i:i + batch_size]
                    placeholders = ",".join("?" * len(batch))

                    cursor.execute(f"""
                        SELECT platform_id FROM comments
                        WHERE platform = ? AND platform_id IN ({placeholders})
                    """, [platform] + batch)

                    for row in cursor.fetchall():
                        result[row["platform_id"]] = True

            return result

        except sqlite3.Error as e:
            logger.error(f"Database error checking comment existence: {e}")
            return result

    def get_existing_comment_ids(
        self,
        client: str,
        platform: str,
        post_ids: Optional[List[str]] = None
    ) -> set:
        """
        Get set of existing comment IDs for efficient duplicate checking.

        Args:
            client: Client name
            platform: Platform name
            post_ids: Optional list of post IDs to filter by

        Returns:
            Set of existing platform_ids
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if post_ids:
                    # Filter by specific posts
                    placeholders = ",".join("?" * len(post_ids))
                    cursor.execute(f"""
                        SELECT platform_id FROM comments
                        WHERE client = ? AND platform = ? AND post_id IN ({placeholders})
                    """, [client, platform] + post_ids)
                else:
                    cursor.execute("""
                        SELECT platform_id FROM comments
                        WHERE client = ? AND platform = ?
                    """, (client, platform))

                return {row["platform_id"] for row in cursor.fetchall()}

        except sqlite3.Error as e:
            logger.error(f"Database error getting existing comment IDs: {e}")
            return set()

    def save_posts(
        self,
        posts: List[Post],
        account: str,
        platform: str
    ) -> str:
        """
        Save multiple posts to storage.

        This method provides compatibility with StorageBackend interface.
        Uses batch operations for better performance.

        Args:
            posts: List of Post objects
            account: Account username (used as client)
            platform: Platform name

        Returns:
            Description of saved data
        """
        saved_count, _ = self.save_posts_batch(account, posts)
        return f"sqlite:{self.db_path}:posts:{account}:{platform}"

    def save_comments(
        self,
        comments: List[Comment],
        account: str,
        platform: str
    ) -> str:
        """
        Save multiple comments to storage.

        This method provides compatibility with StorageBackend interface.
        Uses batch operations for better performance.

        Args:
            comments: List of Comment objects
            account: Account username (used as client)
            platform: Platform name

        Returns:
            Description of saved data
        """
        saved_count, _ = self.save_comments_batch(account, comments)
        return f"sqlite:{self.db_path}:comments:{account}:{platform}"

    def save_extraction_result(
        self,
        posts: List[Post],
        comments: List[Comment],
        profile: Optional[Profile],
        account: str,
        platform: str
    ) -> Dict[str, str]:
        """
        Save complete extraction result.

        This method provides compatibility with StorageBackend interface.

        Args:
            posts: List of Post objects
            comments: List of Comment objects
            profile: Optional Profile object
            account: Account username (used as client)
            platform: Platform name

        Returns:
            Dictionary mapping data type to description
        """
        results = {}

        if posts:
            results["posts"] = self.save_posts(posts, account, platform)

        if comments:
            results["comments"] = self.save_comments(comments, account, platform)

        if profile:
            self.save_profile(account, profile)
            results["profile"] = f"sqlite:{self.db_path}:profile:{account}:{platform}"

        return results


class SQLiteStorageAdapter:
    """
    Adapter to make SQLiteStorage compatible with StorageFactory.

    StorageFactory expects backends that take output_dir as constructor arg,
    but SQLiteStorage takes db_path. This adapter bridges that gap.
    """

    def __new__(cls, output_dir: str):
        """
        Create SQLiteStorage with db path derived from output_dir.

        Args:
            output_dir: Directory for output files (db file placed inside)

        Returns:
            SQLiteStorage instance
        """
        db_path = Path(output_dir) / "storage.db"
        return SQLiteStorage(str(db_path))


# Register SQLiteStorage with StorageFactory for unified access
from .base import StorageFactory
StorageFactory.register("sqlite", SQLiteStorageAdapter)
