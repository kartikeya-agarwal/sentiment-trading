"""GPT API integration for sentiment analysis."""

import openai
from typing import List, Dict, Optional
import json
import time
import hashlib
from functools import lru_cache
from .rate_limiter import RateLimiter, CostTracker


class GPTSentimentAnalyzer:
    """Analyzes sentiment using GPT API."""
    
    def __init__(self, api_key: str, model: str = 'gpt-4o-mini',
                 max_daily_cost: float = 10.0,
                 max_texts_per_request: int = 20):
        """Initialize GPT sentiment analyzer.
        
        Args:
            api_key: OpenAI API key
            model: GPT model to use (default: gpt-4o-mini for cost efficiency)
            max_daily_cost: Maximum daily cost in USD (default: $10)
            max_texts_per_request: Maximum texts to analyze per API call (default: 20)
        """
        openai.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.cache = {}  # Simple in-memory cache
        self.max_texts_per_request = max_texts_per_request
        
        # Initialize rate limiter and cost tracker
        # GPT-4o-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens
        cost_per_1k_input = 0.00015  # $0.15 / 1000 = $0.00015 per 1k tokens
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=60,  # OpenAI allows 500 RPM for tier 1
            max_requests_per_day=1000,
            max_daily_cost=max_daily_cost,
            cost_per_1k_tokens=cost_per_1k_input * 1000  # Convert to per 1M tokens
        )
        self.cost_tracker = CostTracker()
    
    def _get_cache_key(self, text: str, ticker: Optional[str] = None) -> str:
        """Generate cache key for text.
        
        Args:
            text: Text to analyze
            ticker: Optional ticker symbol
            
        Returns:
            Cache key string
        """
        cache_string = f"{ticker or ''}:{text[:200]}"  # Use first 200 chars for cache key
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def analyze_sentiment(self, text: str, ticker: Optional[str] = None) -> Dict:
        """Analyze sentiment for a single text.
        
        Args:
            text: Text to analyze
            ticker: Optional stock ticker symbol for context
            
        Returns:
            Dictionary with sentiment analysis results
        """
        # Check cache first
        cache_key = self._get_cache_key(text, ticker)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check rate limit
        allowed, error_msg = self.rate_limiter.check_rate_limit()
        if not allowed:
            print(f"Rate limit: {error_msg}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "reasoning": f"Rate limit: {error_msg}",
                "confidence": 0.0
            }
        
        # Wait if needed
        self.rate_limiter.wait_if_needed()
        
        try:
            # Construct prompt
            if ticker:
                prompt = f"""Analyze the sentiment for stock {ticker} based on the following text:

"{text}"

Return a JSON object with the following structure:
{{
    "sentiment": "positive", "negative", or "neutral",
    "score": a number between -1.0 (very negative) and 1.0 (very positive),
    "reasoning": a brief explanation (1-2 sentences),
    "confidence": a number between 0.0 and 1.0 indicating confidence in the analysis
}}

Respond only with valid JSON, no additional text."""
            else:
                prompt = f"""Analyze the sentiment of the following text regarding stocks/investing:

"{text}"

Return a JSON object with the following structure:
{{
    "sentiment": "positive", "negative", or "neutral",
    "score": a number between -1.0 (very negative) and 1.0 (very positive),
    "reasoning": a brief explanation (1-2 sentences),
    "confidence": a number between 0.0 and 1.0 indicating confidence in the analysis
}}

Respond only with valid JSON, no additional text."""
            
            # Call GPT API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial sentiment analyst. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            # Track usage and cost
            usage = response.usage
            input_tokens = usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 500
            output_tokens = usage.completion_tokens if hasattr(usage, 'completion_tokens') else 100
            
            # Estimate cost (GPT-4o-mini pricing)
            input_cost = (input_tokens / 1_000_000) * 0.15  # $0.15 per 1M input tokens
            output_cost = (output_tokens / 1_000_000) * 0.60  # $0.60 per 1M output tokens
            total_cost = input_cost + output_cost
            
            # Record request and cost
            self.rate_limiter.record_request(estimated_tokens=input_tokens + output_tokens)
            self.cost_tracker.add_cost(total_cost)
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            # Parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    # Default values if parsing fails
                    result = {
                        "sentiment": "neutral",
                        "score": 0.0,
                        "reasoning": "Unable to parse sentiment",
                        "confidence": 0.0
                    }
            
            # Ensure required fields
            sentiment_data = {
                "sentiment": result.get("sentiment", "neutral"),
                "score": float(result.get("score", 0.0)),
                "reasoning": result.get("reasoning", ""),
                "confidence": float(result.get("confidence", 0.5))
            }
            
            # Cache result
            self.cache[cache_key] = sentiment_data
            
            return sentiment_data
            
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            # Return default neutral sentiment on error
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "reasoning": f"Error: {str(e)}",
                "confidence": 0.0
            }
    
    def batch_analyze(self, texts_list: List[str], ticker: Optional[str] = None,
                     batch_size: int = 5, delay: float = 0.1) -> List[Dict]:
        """Analyze sentiment for multiple texts in batches.
        
        Args:
            texts_list: List of texts to analyze
            ticker: Optional stock ticker symbol
            batch_size: Number of texts to analyze per API call (default: 5)
            delay: Delay between requests in seconds (default: 0.1)
            
        Returns:
            List of sentiment analysis results
        """
        # Limit number of texts to prevent excessive costs
        max_texts = min(len(texts_list), self.max_texts_per_request)
        texts_list = texts_list[:max_texts]
        
        results = []
        
        # Process in batches to optimize API usage
        for i in range(0, len(texts_list), batch_size):
            batch = texts_list[i:i + batch_size]
            
            # Check rate limit before processing batch
            allowed, error_msg = self.rate_limiter.check_rate_limit()
            if not allowed:
                print(f"Rate limit reached during batch processing: {error_msg}")
                # Return cached results or neutral for remaining items
                remaining = len(texts_list) - len(results)
                results.extend([{
                    "sentiment": "neutral",
                    "score": 0.0,
                    "reasoning": "Rate limit reached",
                    "confidence": 0.0
                }] * remaining)
                break
            
            # Analyze each text in the batch
            batch_results = []
            for text in batch:
                result = self.analyze_sentiment(text, ticker)
                batch_results.append(result)
                time.sleep(delay)  # Small delay between requests
            
            results.extend(batch_results)
        
        return results
    
    def get_usage_stats(self) -> Dict:
        """Get usage and cost statistics.
        
        Returns:
            Dictionary with usage stats
        """
        rate_limit_stats = self.rate_limiter.get_stats()
        cost_stats = self.cost_tracker.get_stats()
        
        return {
            **rate_limit_stats,
            **cost_stats
        }
    
    def aggregate_sentiment(self, sentiment_results: List[Dict]) -> Dict:
        """Aggregate multiple sentiment analysis results.
        
        Args:
            sentiment_results: List of sentiment analysis dictionaries
            
        Returns:
            Dictionary with aggregated sentiment metrics
        """
        if not sentiment_results:
            return {
                "overall_sentiment": "neutral",
                "average_score": 0.0,
                "weighted_score": 0.0,
                "confidence": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total_count": 0
            }
        
        # Calculate weighted average (weighted by confidence)
        weighted_sum = 0.0
        total_confidence = 0.0
        scores = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for result in sentiment_results:
            score = result.get("score", 0.0)
            confidence = result.get("confidence", 0.5)
            sentiment = result.get("sentiment", "neutral").lower()
            
            scores.append(score)
            weighted_sum += score * confidence
            total_confidence += confidence
            
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
        
        # Calculate metrics
        average_score = sum(scores) / len(scores) if scores else 0.0
        weighted_score = weighted_sum / total_confidence if total_confidence > 0 else average_score
        avg_confidence = total_confidence / len(sentiment_results) if sentiment_results else 0.0
        
        # Determine overall sentiment
        total_count = len(sentiment_results)
        positive_pct = sentiment_counts["positive"] / total_count if total_count > 0 else 0
        negative_pct = sentiment_counts["negative"] / total_count if total_count > 0 else 0
        
        if weighted_score > 0.3:
            overall_sentiment = "bullish"
        elif weighted_score < -0.3:
            overall_sentiment = "bearish"
        else:
            overall_sentiment = "neutral"
        
        return {
            "overall_sentiment": overall_sentiment,
            "average_score": average_score,
            "weighted_score": weighted_score,
            "confidence": avg_confidence,
            "positive_count": sentiment_counts["positive"],
            "negative_count": sentiment_counts["negative"],
            "neutral_count": sentiment_counts["neutral"],
            "total_count": total_count,
            "positive_percentage": positive_pct * 100,
            "negative_percentage": negative_pct * 100
        }

