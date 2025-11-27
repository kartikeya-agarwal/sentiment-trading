"""Twitter/X scraper for collecting stock sentiment from tweets."""

import tweepy
from typing import List, Dict, Optional
from datetime import datetime
import re


class TwitterScraper:
    """Scrapes Twitter/X for stock-related sentiment."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, 
                 bearer_token: Optional[str] = None):
        """Initialize Twitter scraper with API credentials.
        
        Args:
            api_key: Twitter API key (optional if using bearer token)
            api_secret: Twitter API secret (optional if using bearer token)
            bearer_token: Twitter Bearer Token for API v2
        """
        try:
            if bearer_token:
                # Use Bearer Token for API v2 (recommended)
                self.client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)
            elif api_key and api_secret:
                # Legacy API v1.1 (deprecated but may still work)
                auth = tweepy.AppAuthHandler(api_key, api_secret)
                self.api = tweepy.API(auth, wait_on_rate_limit=True)
                self.client = None
            else:
                print("Warning: No Twitter API credentials provided. Scraping will be limited.")
                self.client = None
                self.api = None
        except Exception as e:
            print(f"Error initializing Twitter client: {e}")
            self.client = None
            self.api = None
    
    def search_tweets(self, query: str, max_results: int = 100,
                     tweet_fields: Optional[List[str]] = None) -> List[Dict]:
        """Search tweets matching a query.
        
        Args:
            query: Search query (stock symbols, $AAPL, etc.)
            max_results: Maximum number of tweets to retrieve (max 100 per request)
            tweet_fields: Optional list of tweet fields to include
            
        Returns:
            List of dictionaries with tweet data
        """
        if not self.client:
            print("Twitter client not initialized. Cannot search tweets.")
            return []
        
        try:
            if tweet_fields is None:
                tweet_fields = ['id', 'text', 'created_at', 'public_metrics', 'author_id']
            
            tweets = []
            # Twitter API v2 allows max 100 results per request
            batch_size = min(max_results, 100)
            
            response = self.client.search_recent_tweets(
                query=query,
                max_results=batch_size,
                tweet_fields=tweet_fields,
                expansions=['author_id']
            )
            
            if not response.data:
                return []
            
            # Create author lookup
            authors = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    authors[user.id] = user.username
            
            for tweet in response.data:
                metrics = tweet.public_metrics if hasattr(tweet, 'public_metrics') else {}
                tweet_data = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'retweets': metrics.get('retweet_count', 0),
                    'likes': metrics.get('like_count', 0),
                    'replies': metrics.get('reply_count', 0),
                    'timestamp': tweet.created_at,
                    'author': authors.get(tweet.author_id, 'unknown') if hasattr(tweet, 'author_id') else 'unknown',
                    'stock_mentions': self._extract_stock_mentions(tweet.text)
                }
                tweets.append(tweet_data)
            
            return tweets
        except Exception as e:
            print(f"Error searching tweets: {e}")
            return []
    
    def get_tweets_for_ticker(self, ticker: str, max_results: int = 50) -> List[Dict]:
        """Get tweets specifically mentioning a stock ticker.
        
        Args:
            ticker: Stock ticker symbol
            max_results: Maximum number of tweets to retrieve
            
        Returns:
            List of dictionaries with tweet data
        """
        # Search for both $TICKER and TICKER
        queries = [f'${ticker}', f'{ticker} stock']
        all_tweets = []
        
        for query in queries:
            tweets = self.search_tweets(query, max_results=max_results // len(queries))
            all_tweets.extend(tweets)
        
        # Remove duplicates based on tweet ID
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet['id'] not in seen_ids:
                seen_ids.add(tweet['id'])
                unique_tweets.append(tweet)
        
        return unique_tweets[:max_results]
    
    def _extract_stock_mentions(self, text: str) -> List[str]:
        """Extract stock ticker mentions from text (e.g., $AAPL, AAPL).
        
        Args:
            text: Text to search for stock mentions
            
        Returns:
            List of mentioned stock tickers
        """
        # Pattern for $TICKER format
        dollar_pattern = r'\$([A-Z]{1,5})\b'
        
        tickers = set()
        
        # Find $TICKER mentions
        dollar_matches = re.findall(dollar_pattern, text.upper())
        tickers.update(dollar_matches)
        
        return list(tickers)
    
    def get_trending_stock_tweets(self, max_results: int = 50) -> List[Dict]:
        """Get tweets about trending stock-related topics.
        
        Note: This is a placeholder as Twitter API v2 doesn't directly provide trending topics.
        In practice, you would search for common stock-related hashtags or keywords.
        
        Args:
            max_results: Maximum number of tweets to retrieve
            
        Returns:
            List of dictionaries with tweet data
        """
        # Search for common stock-related hashtags
        trending_queries = [
            '#stocks', '#stockmarket', '#trading', '#investing',
            '$SPY', '$QQQ', '#crypto', '#bitcoin'
        ]
        
        all_tweets = []
        tweets_per_query = max_results // len(trending_queries)
        
        for query in trending_queries:
            tweets = self.search_tweets(query, max_results=tweets_per_query)
            all_tweets.extend(tweets)
        
        # Remove duplicates
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet['id'] not in seen_ids:
                seen_ids.add(tweet['id'])
                unique_tweets.append(tweet)
        
        return unique_tweets[:max_results]

