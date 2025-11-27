"""Reddit scraper for collecting stock sentiment from Reddit posts."""

import praw
from typing import List, Dict, Optional
from datetime import datetime
import re


class RedditScraper:
    """Scrapes Reddit posts for stock-related sentiment."""
    
    def __init__(self, reddit_client_id: str, reddit_secret: str, user_agent: str):
        """Initialize Reddit scraper with PRAW client.
        
        Args:
            reddit_client_id: Reddit API client ID
            reddit_secret: Reddit API secret
            user_agent: User agent string for Reddit API
        """
        try:
            self.reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_secret,
                user_agent=user_agent
            )
            self.reddit.read_only = True
        except Exception as e:
            print(f"Error initializing Reddit client: {e}")
            self.reddit = None
    
    def scrape_subreddit(self, subreddit_name: str, limit: int = 100, 
                        time_filter: str = 'day') -> List[Dict]:
        """Scrape posts from a subreddit.
        
        Args:
            subreddit_name: Name of the subreddit to scrape
            limit: Maximum number of posts to retrieve
            time_filter: Time filter ('all', 'day', 'hour', 'month', 'week', 'year')
            
        Returns:
            List of dictionaries with post data
        """
        if not self.reddit:
            return []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            for post in subreddit.top(time_filter=time_filter, limit=limit):
                post_data = {
                    'title': post.title,
                    'content': post.selftext if post.selftext else '',
                    'upvotes': post.score,
                    'comments': post.num_comments,
                    'timestamp': datetime.fromtimestamp(post.created_utc),
                    'url': post.url,
                    'author': str(post.author) if post.author else 'unknown',
                    'stock_mentions': self._extract_stock_mentions(post.title + ' ' + post.selftext),
                    'subreddit': subreddit_name
                }
                posts.append(post_data)
            
            return posts
        except Exception as e:
            print(f"Error scraping subreddit {subreddit_name}: {e}")
            return []
    
    def search_posts(self, query: str, limit: int = 100, 
                    subreddits: Optional[List[str]] = None) -> List[Dict]:
        """Search for posts matching a query.
        
        Args:
            query: Search query (e.g., stock ticker)
            limit: Maximum number of posts to retrieve
            subreddits: Optional list of subreddits to search in
            
        Returns:
            List of dictionaries with matching posts
        """
        if not self.reddit:
            return []
        
        try:
            posts = []
            search_limit = min(limit, 100)  # Reddit API limit per request
            
            if subreddits:
                for subreddit_name in subreddits:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    for post in subreddit.search(query, limit=search_limit, sort='hot'):
                        post_data = {
                            'title': post.title,
                            'content': post.selftext if post.selftext else '',
                            'upvotes': post.score,
                            'comments': post.num_comments,
                            'timestamp': datetime.fromtimestamp(post.created_utc),
                            'url': post.url,
                            'author': str(post.author) if post.author else 'unknown',
                            'stock_mentions': self._extract_stock_mentions(post.title + ' ' + post.selftext),
                            'subreddit': subreddit_name
                        }
                        posts.append(post_data)
                        if len(posts) >= limit:
                            break
                    if len(posts) >= limit:
                        break
            else:
                # Search across all subreddits
                for post in self.reddit.subreddit('all').search(query, limit=search_limit, sort='hot'):
                    post_data = {
                        'title': post.title,
                        'content': post.selftext if post.selftext else '',
                        'upvotes': post.score,
                        'comments': post.num_comments,
                        'timestamp': datetime.fromtimestamp(post.created_utc),
                        'url': post.url,
                        'author': str(post.author) if post.author else 'unknown',
                        'stock_mentions': self._extract_stock_mentions(post.title + ' ' + post.selftext),
                        'subreddit': post.subreddit.display_name
                    }
                    posts.append(post_data)
                    if len(posts) >= limit:
                        break
            
            return posts[:limit]
        except Exception as e:
            print(f"Error searching Reddit posts: {e}")
            return []
    
    def _extract_stock_mentions(self, text: str) -> List[str]:
        """Extract stock ticker mentions from text (e.g., $AAPL, AAPL).
        
        Args:
            text: Text to search for stock mentions
            
        Returns:
            List of mentioned stock tickers
        """
        # Pattern for $TICKER format
        dollar_pattern = r'\$([A-Z]{1,5})\b'
        # Pattern for standalone tickers (common ones)
        standalone_pattern = r'\b([A-Z]{1,5})\b'
        
        tickers = set()
        
        # Find $TICKER mentions
        dollar_matches = re.findall(dollar_pattern, text.upper())
        tickers.update(dollar_matches)
        
        # Common stock tickers to check (major ones)
        common_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
        for ticker in common_tickers:
            if ticker in text.upper():
                tickers.add(ticker)
        
        return list(tickers)
    
    def get_posts_for_ticker(self, ticker: str, limit: int = 50,
                             subreddits: Optional[List[str]] = None) -> List[Dict]:
        """Get posts specifically mentioning a stock ticker.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of posts to retrieve
            subreddits: Optional list of subreddits to search in
            
        Returns:
            List of dictionaries with post data
        """
        # Search for both $TICKER and TICKER
        queries = [f'${ticker}', ticker]
        all_posts = []
        
        for query in queries:
            posts = self.search_posts(query, limit=limit // len(queries), subreddits=subreddits)
            all_posts.extend(posts)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_posts = []
        for post in all_posts:
            if post['url'] not in seen_urls:
                seen_urls.add(post['url'])
                unique_posts.append(post)
        
        return unique_posts[:limit]

