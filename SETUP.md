# Setup Instructions

## Prerequisites

1. Python 3.8 or higher
2. API Keys for:
   - OpenAI (for GPT sentiment analysis)
   - Reddit (optional, for Reddit scraping)
   - Twitter/X (optional, for Twitter scraping)

## Installation

1. Clone or navigate to the project directory:
```bash
cd Sentiment-Trading
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env file and add your API keys:
# OPENAI_API_KEY=your_key_here
# REDDIT_CLIENT_ID=your_client_id_here
# REDDIT_SECRET=your_secret_here
# TWITTER_BEARER_TOKEN=your_token_here
```

## Running the Application

1. Start the Flask server:
```bash
python run.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

### Analyzing a Stock

1. Enter a stock ticker (e.g., AAPL, MSFT, TSLA) in the search bar
2. Click "Analyze" or press Enter
3. View:
   - Trading recommendation (Buy/Sell/Hold)
   - Sentiment analysis
   - Price charts with technical indicators
   - Recent mentions from Reddit, Twitter, and news sources

### Running a Backtest

1. Enter a ticker symbol
2. Select start and end dates
3. Click "Run Backtest"
4. View performance metrics and comparison with S&P 500

## API Endpoints

- `GET /api/sentiment/<ticker>` - Get current sentiment for a ticker
- `GET /api/recommendation/<ticker>` - Get trading recommendation
- `GET /api/charts/<ticker>` - Get chart data with sentiment overlay
- `POST /api/backtest` - Run backtest with parameters
- `GET /api/historical-sentiment/<ticker>` - Get historical sentiment data

## Notes

- The application uses GPT-4o-mini by default for cost efficiency
- Sentiment results are cached to reduce API costs
- Market data is fetched from Yahoo Finance (free, no API key required)
- Reddit and Twitter scrapers require API credentials (optional)

## Troubleshooting

1. **Import errors**: Make sure you're running from the project root directory
2. **API key errors**: Verify your `.env` file is properly configured
3. **Database errors**: The SQLite database will be created automatically on first run
4. **Scraping errors**: Check your API credentials if Reddit/Twitter scraping fails

