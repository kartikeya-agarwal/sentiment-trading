# Sentiment Trading System

A comprehensive sentiment-based trading system that scrapes stock sentiment from Reddit, Twitter/X, and news sources, analyzes it using GPT API, and provides trading recommendations with backtesting capabilities.

## Features

- **Data Collection**: Scrapes sentiment from Reddit, Twitter/X, and news sources
- **Market Data**: Fetches historical and real-time data from Yahoo Finance
- **Sentiment Analysis**: Uses GPT API for advanced NLP sentiment analysis
- **Trading Strategy**: Combines sentiment and technical indicators for trading signals
- **Backtesting**: Tests strategies on historical data with S&P 500 benchmark comparison
- **Web Frontend**: User-friendly dashboard with charts and recommendations

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up API keys (see `API_KEYS.md` for detailed instructions):
   - **REQUIRED:** OpenAI API key (for sentiment analysis)
   - **OPTIONAL:** Reddit API credentials, Twitter/X Bearer Token
   
   Create a `.env` file in the project root:
```bash
# Create .env file
touch .env

# Add your keys (minimum: OpenAI API key)
echo "OPENAI_API_KEY=your_key_here" >> .env
```

For full instructions on obtaining API keys, see [API_KEYS.md](API_KEYS.md).

3. Run the application:
```bash
python run.py
```

Alternatively:
```bash
cd src/api
python app.py
```

4. Open your browser to `http://localhost:5000`

## Configuration

Edit `config/config.yaml` to customize:
- Scraping sources and frequency
- Strategy parameters (sentiment vs technical weights)
- Backtesting parameters
- **Rate limiting and cost controls** (important for managing API costs)

### Rate Limiting & Cost Control

The system includes built-in rate limiting and cost tracking to prevent excessive API spending:

- **Default limits:**
  - Max 60 requests per minute
  - Max 1,000 requests per day
  - Max $10 USD daily cost limit
  - Max 20 texts analyzed per sentiment request

- **Monitor usage:** Visit `/api/usage-stats` endpoint to see:
  - Current request counts
  - Daily costs
  - Remaining budget
  - Weekly/monthly totals

- **Adjust limits:** Edit `config/config.yaml` under `rate_limiting` section

- **Cost tracking:** Costs are automatically tracked and saved to `cost_tracker.json`

## API Endpoints

- `GET /api/sentiment/<ticker>` - Get current sentiment for a ticker
- `GET /api/recommendation/<ticker>` - Get trading recommendation
- `POST /api/backtest` - Run backtest with parameters
- `GET /api/charts/<ticker>` - Get chart data with sentiment overlay
- `GET /api/historical-sentiment/<ticker>` - Get historical sentiment data

## License

MIT

