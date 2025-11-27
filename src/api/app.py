"""Flask application for sentiment trading system API."""

import os
import yaml
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Add src directory to path for imports
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, src_dir)

from database.db_manager import DatabaseManager
from market_data.yahoo_finance import MarketDataFetcher
from sentiment.gpt_analyzer import GPTSentimentAnalyzer
from strategy.trading_strategy import SentimentTradingStrategy
from strategy.backtesting_engine import BacktestingEngine
from data_collection.reddit_scraper import RedditScraper
from data_collection.twitter_scraper import TwitterScraper
from data_collection.news_scraper import NewsScraper

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='../../frontend/static', template_folder='../../frontend/templates')
CORS(app)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Initialize components
db_manager = DatabaseManager()

# Initialize market data fetcher
market_fetcher = MarketDataFetcher()

# Initialize sentiment analyzer with rate limiting
openai_api_key = os.getenv('OPENAI_API_KEY') or config.get('api_keys', {}).get('openai_api_key', '')
rate_limit_config = config.get('rate_limiting', {})
sentiment_analyzer = GPTSentimentAnalyzer(
    openai_api_key, 
    model='gpt-4o-mini',
    max_daily_cost=rate_limit_config.get('max_daily_cost_usd', 10.0),
    max_texts_per_request=rate_limit_config.get('max_texts_per_sentiment_request', 20)
)

# Initialize scrapers
reddit_client_id = os.getenv('REDDIT_CLIENT_ID') or config.get('api_keys', {}).get('reddit_client_id', '')
reddit_secret = os.getenv('REDDIT_SECRET') or config.get('api_keys', {}).get('reddit_secret', '')
twitter_bearer = os.getenv('TWITTER_BEARER_TOKEN') or config.get('api_keys', {}).get('twitter_bearer_token', '')

reddit_scraper = RedditScraper(reddit_client_id, reddit_secret, 'sentiment-trading-bot/1.0') if reddit_client_id else None
twitter_scraper = TwitterScraper(bearer_token=twitter_bearer) if twitter_bearer else None
news_scraper = NewsScraper()

# Initialize strategy
strategy_config = config.get('strategy', {})
trading_strategy = SentimentTradingStrategy(
    sentiment_weight=strategy_config.get('sentiment_weight', 0.6),
    technical_weight=strategy_config.get('technical_weight', 0.4),
    buy_threshold=strategy_config.get('buy_threshold', 0.6),
    sell_threshold=strategy_config.get('sell_threshold', -0.6)
)

# Initialize backtesting engine
backtest_config = config.get('backtesting', {})
backtesting_engine = BacktestingEngine(
    initial_capital=backtest_config.get('initial_capital', 100000),
    transaction_cost=backtest_config.get('transaction_cost', 0.001)
)


@app.route('/')
def index():
    """Serve the main dashboard."""
    return send_from_directory(app.template_folder, 'index.html')


@app.route('/api/sentiment/<ticker>')
def get_sentiment(ticker):
    """Get current sentiment for a ticker.
    
    Returns:
        JSON with aggregated sentiment, recent mentions, and charts data
    """
    try:
        ticker = ticker.upper()
        
        # Collect sentiment data from various sources
        texts_for_analysis = []
        sources = []
        
        # Scrape Reddit
        if reddit_scraper:
            try:
                reddit_posts = reddit_scraper.get_posts_for_ticker(ticker, limit=20)
                for post in reddit_posts:
                    text = post.get('title', '') + ' ' + post.get('content', '')
                    if text.strip():
                        texts_for_analysis.append(text)
                        sources.append({
                            'source': 'reddit',
                            'text': text[:200] + '...' if len(text) > 200 else text,
                            'metadata': {
                                'subreddit': post.get('subreddit'),
                                'upvotes': post.get('upvotes', 0),
                                'url': post.get('url')
                            }
                        })
            except Exception as e:
                print(f"Error scraping Reddit: {e}")
        
        # Scrape Twitter
        if twitter_scraper:
            try:
                twitter_tweets = twitter_scraper.get_tweets_for_ticker(ticker, max_results=20)
                for tweet in twitter_tweets:
                    text = tweet.get('text', '')
                    if text.strip():
                        texts_for_analysis.append(text)
                        sources.append({
                            'source': 'twitter',
                            'text': text[:200] + '...' if len(text) > 200 else text,
                            'metadata': {
                                'likes': tweet.get('likes', 0),
                                'retweets': tweet.get('retweets', 0),
                                'author': tweet.get('author')
                            }
                        })
            except Exception as e:
                print(f"Error scraping Twitter: {e}")
        
        # Scrape News
        try:
            news_articles = news_scraper.search_news_by_ticker(ticker, limit_per_source=10)
            for article in news_articles[:20]:
                text = article.get('headline', '') + ' ' + article.get('article_text', '')
                if text.strip():
                    texts_for_analysis.append(text)
                    sources.append({
                        'source': 'news',
                        'text': text[:200] + '...' if len(text) > 200 else text,
                        'metadata': {
                            'headline': article.get('headline'),
                            'url': article.get('url'),
                            'source': article.get('source')
                        }
                    })
        except Exception as e:
            print(f"Error scraping news: {e}")
        
        # Analyze sentiment (limit texts to prevent excessive costs)
        max_texts = rate_limit_config.get('max_texts_per_sentiment_request', 20)
        texts_for_analysis = texts_for_analysis[:max_texts]
        
        if texts_for_analysis:
            sentiment_results = sentiment_analyzer.batch_analyze(
                texts_for_analysis, 
                ticker=ticker, 
                batch_size=5,
                delay=0.2  # Increased delay to respect rate limits
            )
            aggregated = sentiment_analyzer.aggregate_sentiment(sentiment_results)
        else:
            aggregated = sentiment_analyzer.aggregate_sentiment([])
        
        # Get historical sentiment from database
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        historical_sentiment = db_manager.get_historical_sentiment(ticker, start_date, end_date)
        
        return jsonify({
            'ticker': ticker,
            'aggregated_sentiment': aggregated,
            'recent_mentions': sources[:10],  # Return top 10
            'historical_sentiment': historical_sentiment.to_dict('records') if not historical_sentiment.empty else []
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommendation/<ticker>')
def get_recommendation(ticker):
    """Get trading recommendation for a ticker.
    
    Returns:
        JSON with buy/sell/hold signal, confidence, reasoning, and supporting data
    """
    try:
        ticker = ticker.upper()
        
        # Get sentiment data
        sentiment_response = get_sentiment(ticker)
        sentiment_data = sentiment_response.get_json() if hasattr(sentiment_response, 'get_json') else {}
        aggregated_sentiment = sentiment_data.get('aggregated_sentiment', {})
        
        # Get market data and indicators
        indicators = market_fetcher.get_market_indicators(ticker)
        market_data = {
            'indicators': indicators,
            'current_price': indicators.get('current_price')
        }
        
        # Generate signal
        signal = trading_strategy.generate_signal(ticker, aggregated_sentiment, market_data)
        
        # Save signal to database
        db_manager.save_trading_signal({
            'ticker': ticker,
            'signal_type': signal['signal_type'],
            'confidence': signal['confidence'],
            'sentiment_score': signal['sentiment_score'],
            'technical_indicators': signal['technical_indicators'],
            'timestamp': datetime.now(),
            'reasoning': signal['reasoning']
        })
        
        return jsonify({
            'ticker': ticker,
            'signal': signal,
            'sentiment_data': aggregated_sentiment,
            'market_data': market_data
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Run backtest with specified parameters.
    
    Expected JSON body:
        {
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "strategy_params": {
                "sentiment_weight": 0.6,
                "technical_weight": 0.4
            }
        }
    """
    try:
        data = request.get_json()
        ticker = data.get('ticker', 'AAPL').upper()
        start_date = datetime.fromisoformat(data.get('start_date', '2023-01-01'))
        end_date = datetime.fromisoformat(data.get('end_date', '2024-01-01'))
        
        # Create strategy with custom parameters if provided
        strategy_params = data.get('strategy_params', {})
        if strategy_params:
            backtest_strategy = SentimentTradingStrategy(
                sentiment_weight=strategy_params.get('sentiment_weight', 0.6),
                technical_weight=strategy_params.get('technical_weight', 0.4),
                buy_threshold=strategy_params.get('buy_threshold', 0.6),
                sell_threshold=strategy_params.get('sell_threshold', -0.6)
            )
        else:
            backtest_strategy = trading_strategy
        
        # Run backtest
        result = backtesting_engine.run_backtest(
            backtest_strategy,
            ticker,
            start_date,
            end_date,
            db_manager=db_manager
        )
        
        # Save result to database
        if 'error' not in result:
            db_manager.save_backtest_result({
                'strategy_name': 'Sentiment Trading Strategy',
                'ticker': ticker,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': backtesting_engine.initial_capital,
                'final_value': result.get('final_value'),
                'total_return': result.get('total_return'),
                'sharpe_ratio': result.get('sharpe_ratio'),
                'max_drawdown': result.get('max_drawdown'),
                'win_rate': result.get('win_rate'),
                'vs_sp500_performance': result.get('vs_sp500_performance'),
                'daily_returns': result.get('daily_returns')
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/charts/<ticker>')
def get_charts_data(ticker):
    """Get market data and sentiment overlay for charts.
    
    Returns:
        JSON with OHLCV data, sentiment timeline, and technical indicators
    """
    try:
        ticker = ticker.upper()
        
        # Get market data
        market_df = market_fetcher.get_historical_data(ticker, period='1y')
        
        # Get indicators
        indicators_data = market_fetcher.get_market_indicators(ticker, period='1y')
        
        # Get historical sentiment
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        sentiment_df = db_manager.get_historical_sentiment(ticker, start_date, end_date)
        
        # Format data for charts
        chart_data = {
            'ticker': ticker,
            'market_data': market_df.to_dict('records') if not market_df.empty else [],
            'indicators': indicators_data,
            'sentiment_timeline': sentiment_df.to_dict('records') if not sentiment_df.empty else []
        }
        
        return jsonify(chart_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/usage-stats')
def get_usage_stats():
    """Get API usage and cost statistics.
    
    Returns:
        JSON with usage stats and costs
    """
    try:
        stats = sentiment_analyzer.get_usage_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/historical-sentiment/<ticker>')
def get_historical_sentiment(ticker):
    """Get historical sentiment data for a ticker.
    
    Query parameters:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    try:
        ticker = ticker.upper()
        start_date_str = request.args.get('start_date', None)
        end_date_str = request.args.get('end_date', None)
        
        if start_date_str and end_date_str:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        
        sentiment_df = db_manager.get_historical_sentiment(ticker, start_date, end_date)
        
        return jsonify({
            'ticker': ticker,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'data': sentiment_df.to_dict('records') if not sentiment_df.empty else []
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)

