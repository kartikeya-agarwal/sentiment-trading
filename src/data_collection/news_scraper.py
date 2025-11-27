"""News scraper for collecting stock sentiment from finance news sources."""

import feedparser
from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Optional
from datetime import datetime
import re


class NewsScraper:
    """Scrapes finance news from various sources."""
    
    def __init__(self):
        """Initialize news scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # RSS feed URLs for finance news sources
        self.rss_feeds = {
            'reuters': 'https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best',
            'bloomberg': 'https://feeds.bloomberg.com/markets/news.rss',
            'cnbc': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
            'yahoo_finance': 'https://finance.yahoo.com/news/rssindex',
            'marketwatch': 'http://feeds.marketwatch.com/marketwatch/topstories/'
        }
    
    def scrape_finance_news(self, sources: Optional[List[str]] = None, 
                           limit_per_source: int = 20) -> List[Dict]:
        """Scrape finance news from specified sources.
        
        Args:
            sources: List of news sources to scrape (default: all available)
            limit_per_source: Maximum number of articles per source
            
        Returns:
            List of dictionaries with news article data
        """
        if sources is None:
            sources = list(self.rss_feeds.keys())
        
        all_articles = []
        
        for source in sources:
            if source not in self.rss_feeds:
                print(f"Unknown source: {source}")
                continue
            
            try:
                articles = self._scrape_rss_feed(self.rss_feeds[source], source, limit_per_source)
                all_articles.extend(articles)
            except Exception as e:
                print(f"Error scraping {source}: {e}")
        
        return all_articles
    
    def _scrape_rss_feed(self, feed_url: str, source: str, limit: int = 20) -> List[Dict]:
        """Scrape articles from an RSS feed.
        
        Args:
            feed_url: URL of the RSS feed
            source: Name of the news source
            limit: Maximum number of articles to retrieve
            
        Returns:
            List of dictionaries with article data
        """
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            
            for entry in feed.entries[:limit]:
                # Parse published date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    try:
                        published = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                    except:
                        published = datetime.utcnow()
                
                # Extract article text
                article_text = ''
                if hasattr(entry, 'summary'):
                    article_text = entry.summary
                elif hasattr(entry, 'description'):
                    article_text = entry.description
                
                # Try to fetch full article content
                full_text = article_text
                if hasattr(entry, 'link'):
                    try:
                        full_text = self._fetch_article_content(entry.link)
                    except:
                        pass  # Use summary if full content fetch fails
                
                article_data = {
                    'headline': entry.title if hasattr(entry, 'title') else '',
                    'article_text': full_text or article_text,
                    'summary': article_text,
                    'timestamp': published or datetime.utcnow(),
                    'url': entry.link if hasattr(entry, 'link') else '',
                    'source': source,
                    'stock_mentions': self._extract_stock_mentions(
                        entry.title + ' ' + full_text
                    )
                }
                articles.append(article_data)
            
            return articles
        except Exception as e:
            print(f"Error parsing RSS feed {feed_url}: {e}")
            return []
    
    def _fetch_article_content(self, url: str) -> str:
        """Fetch full article content from URL.
        
        Args:
            url: URL of the article
            
        Returns:
            Article text content
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find article content in common HTML tags
            article_content = ''
            
            # Common article content selectors
            selectors = [
                'article',
                '.article-body',
                '.article-content',
                '.post-content',
                'main',
                '#article-body',
                '[class*="article"]',
                '[class*="content"]'
            ]
            
            for selector in selectors:
                content = soup.select_one(selector)
                if content:
                    article_content = content.get_text(separator=' ', strip=True)
                    if len(article_content) > 200:  # Minimum content length
                        break
            
            # Fallback: get all paragraph text
            if not article_content:
                paragraphs = soup.find_all('p')
                article_content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            return article_content[:5000]  # Limit length
        except Exception as e:
            print(f"Error fetching article content from {url}: {e}")
            return ''
    
    def search_news_by_ticker(self, ticker: str, sources: Optional[List[str]] = None,
                              limit_per_source: int = 10) -> List[Dict]:
        """Search news articles mentioning a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            sources: Optional list of sources to search
            limit_per_source: Maximum articles per source
            
        Returns:
            List of dictionaries with relevant articles
        """
        all_articles = self.scrape_finance_news(sources=sources, limit_per_source=limit_per_source * 5)
        
        # Filter articles that mention the ticker
        relevant_articles = []
        ticker_upper = ticker.upper()
        
        for article in all_articles:
            text = article['headline'] + ' ' + article['article_text']
            if ticker_upper in text.upper() or ticker in article.get('stock_mentions', []):
                relevant_articles.append(article)
                if len(relevant_articles) >= limit_per_source * len(sources or ['all']):
                    break
        
        return relevant_articles
    
    def _extract_stock_mentions(self, text: str) -> List[str]:
        """Extract stock ticker mentions from text.
        
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
        
        # Common stock tickers (major ones)
        common_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
                         'SPY', 'QQQ', 'DIA', 'VIX']
        for ticker in common_tickers:
            if ticker in text.upper():
                tickers.add(ticker)
        
        return list(tickers)

