# Configuration for Real Extraction

## Facebook Cookies

Facebook scraping requires cookies from a logged-in session:

1. Log into Facebook in Chrome
2. Install a cookie export extension (like "EditThisCookie" or "Get cookies.txt")
3. Export cookies to `config/facebook_cookies.json`
4. Set in `.env`:
   ```
   EXTRACTOR_FACEBOOK__COOKIES_FILE=config/facebook_cookies.json
   ```

## Instagram Login

Instagram requires authentication:

1. Create a `.env` file in the project root:
   ```
   EXTRACTOR_INSTAGRAM__USERNAME=your_instagram_username
   EXTRACTOR_INSTAGRAM__PASSWORD=your_instagram_password
   ```

2. Or use a session file (more secure):
   ```bash
   # Login once and save session
   instaloader --login your_username
   # Then set:
   EXTRACTOR_INSTAGRAM__SESSION_FILE=~/.config/instaloader/session-your_username
   ```

## Testing with Public Data

For testing without authentication, you can use the batch configuration
which will save whatever data it can get (even if limited).

## Alternative: Apify (Paid)

For reliable extraction, consider Apify actors:
- Facebook: https://apify.com/apify/facebook-posts-scraper
- Instagram: https://apify.com/apify/instagram-scraper

These cost ~$2-5 per 1000 posts but are more reliable.
