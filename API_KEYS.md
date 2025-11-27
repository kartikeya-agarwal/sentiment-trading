# API Keys Guide

This document explains which API keys you need to obtain and how to set them up.

## Required API Key

### ✅ **OpenAI API Key** (REQUIRED)

**Why it's required:** The core sentiment analysis functionality depends on the GPT API.

**How to get it:**
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to **API Keys** section
4. Click **"Create new secret key"**
5. Copy the key (you'll only see it once!)

**Cost:** 
- Uses GPT-4o-mini by default (cost-efficient)
- Pricing: ~$0.15 per 1M input tokens, $0.60 per 1M output tokens
- System has built-in rate limiting (default: $10/day max)
- Typical analysis: ~$0.01-0.05 per stock analysis

**Set in `.env`:**
```bash
OPENAI_API_KEY=sk-your-key-here
```

---

## Optional API Keys

These are **optional** but provide additional data sources. The system will work with just OpenAI, but you'll get richer sentiment data with these.

### 🔵 **Reddit API Credentials** (OPTIONAL)

**Why it's optional:** The system can work with just news scraping, but Reddit provides valuable community sentiment.

**How to get it:**
1. Go to [Reddit Apps](https://www.reddit.com/prefs/apps)
2. Scroll down and click **"create another app"** or **"create an app"**
3. Fill in:
   - **Name:** "Sentiment Trading Bot" (or any name)
   - **App type:** Select **"script"**
   - **Description:** "Stock sentiment analysis tool"
   - **About URL:** (leave blank or use your website)
   - **Redirect URI:** `http://localhost:5000` (not critical for read-only)
4. Click **"create app"**
5. You'll see:
   - **Client ID:** The string under your app name (looks like: `abc123def456ghi789`)
   - **Secret:** The "secret" field (shows as `-` until you reveal it)

**Set in `.env`:**
```bash
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_SECRET=your_secret_here
```

**Note:** Reddit API is free and doesn't require payment for basic usage.

---

### 🔵 **Twitter/X Bearer Token** (OPTIONAL)

**Why it's optional:** Twitter provides real-time sentiment, but requires API access.

**How to get it:**
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Sign up for a developer account (approval may take time)
3. Create a new Project and App
4. Navigate to **Keys and Tokens**
5. Generate a **Bearer Token**

**Set in `.env`:**
```bash
TWITTER_BEARER_TOKEN=your_bearer_token_here
```

**Note:** Twitter API access can be limited or require paid tiers depending on your account type. The system will work fine without it.

---

## Setup Instructions

1. **Create `.env` file** in the project root:
```bash
cp .env.example .env
# Or create manually: touch .env
```

2. **Add your API keys** to `.env`:
```bash
# REQUIRED
OPENAI_API_KEY=sk-your-openai-key-here

# OPTIONAL (uncomment and add if you have them)
# REDDIT_CLIENT_ID=your_reddit_client_id
# REDDIT_SECRET=your_reddit_secret
# TWITTER_BEARER_TOKEN=your_twitter_token
```

3. **Save the file** (make sure it's in `.gitignore` - it should be by default)

4. **Run the application:**
```bash
python run.py
```

---

## What Works Without Optional Keys?

### With **ONLY OpenAI API Key:**
- ✅ Sentiment analysis using GPT
- ✅ Market data from Yahoo Finance (free, no key needed)
- ✅ News scraping (free RSS feeds, no key needed)
- ✅ Trading recommendations
- ✅ Backtesting
- ✅ All charts and visualizations
- ❌ Reddit sentiment (skipped gracefully)
- ❌ Twitter sentiment (skipped gracefully)

### With **OpenAI + Reddit:**
- ✅ Everything above
- ✅ Reddit sentiment from r/wallstreetbets, r/stocks, etc.

### With **All Keys:**
- ✅ Full functionality with all data sources

---

## Testing Your Setup

After setting up your API keys, you can test:

1. **Check if OpenAI key works:**
   - Try analyzing a stock (e.g., AAPL)
   - If you see sentiment results, it's working!

2. **Check rate limiting:**
   - Visit: `http://localhost:5000/api/usage-stats`
   - You should see your usage and cost stats

3. **Verify optional keys:**
   - Check console logs when running - if Reddit/Twitter keys are missing, you'll see warnings but the app continues

---

## Security Notes

⚠️ **Never commit your `.env` file to git!**
- The `.gitignore` file already excludes `.env`
- Never share your API keys publicly
- If a key is exposed, regenerate it immediately from the provider's dashboard

---

## Troubleshooting

**"OpenAI API key not found" error:**
- Make sure `.env` file exists in project root
- Check that `OPENAI_API_KEY=sk-...` is on a single line
- No quotes needed around the key
- Restart the application after adding keys

**Reddit/Twitter not working:**
- Check console for error messages
- Verify keys are correct (no extra spaces)
- For Reddit: Make sure you selected "script" app type
- For Twitter: Ensure your developer account is approved

---

## Cost Estimates

**Typical daily costs (with default $10/day limit):**
- Small usage (5-10 stock analyses): ~$0.50-1.00
- Medium usage (20-30 analyses): ~$2.00-4.00
- Heavy usage: Up to $10/day (enforced limit)

The system automatically tracks and limits costs, so you won't exceed your budget.

