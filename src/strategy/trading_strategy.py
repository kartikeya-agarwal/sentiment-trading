"""Trading strategy module combining sentiment and technical indicators."""

from typing import Dict, Optional, List
import numpy as np


class SentimentTradingStrategy:
    """Trading strategy that combines sentiment analysis with technical indicators."""
    
    def __init__(self, sentiment_weight: float = 0.6, technical_weight: float = 0.4,
                 buy_threshold: float = 0.6, sell_threshold: float = -0.6):
        """Initialize trading strategy.
        
        Args:
            sentiment_weight: Weight for sentiment score (0-1)
            technical_weight: Weight for technical indicators (0-1)
            buy_threshold: Threshold above which to generate BUY signal
            sell_threshold: Threshold below which to generate SELL signal
        """
        self.sentiment_weight = sentiment_weight
        self.technical_weight = technical_weight
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        
        # Ensure weights sum to 1.0
        total_weight = sentiment_weight + technical_weight
        if total_weight > 0:
            self.sentiment_weight = sentiment_weight / total_weight
            self.technical_weight = technical_weight / total_weight
    
    def generate_signal(self, ticker: str, sentiment_data: Dict, 
                       market_data: Dict) -> Dict:
        """Generate trading signal based on sentiment and market data.
        
        Args:
            ticker: Stock ticker symbol
            sentiment_data: Dictionary with aggregated sentiment metrics
            market_data: Dictionary with technical indicators
            
        Returns:
            Dictionary with trading signal (buy/sell/hold), confidence, and reasoning
        """
        # Calculate sentiment score (normalized to -1 to 1)
        sentiment_score = sentiment_data.get('weighted_score', 0.0)
        sentiment_confidence = sentiment_data.get('confidence', 0.5)
        
        # Calculate technical score from indicators
        technical_score = self._calculate_technical_score(market_data)
        technical_confidence = self._calculate_technical_confidence(market_data)
        
        # Combine scores with weights
        final_score = (self.sentiment_weight * sentiment_score + 
                      self.technical_weight * technical_score)
        
        # Calculate overall confidence
        overall_confidence = (self.sentiment_weight * sentiment_confidence + 
                            self.technical_weight * technical_confidence)
        
        # Determine signal type
        if final_score > self.buy_threshold:
            signal_type = 'buy'
        elif final_score < self.sell_threshold:
            signal_type = 'sell'
        else:
            signal_type = 'hold'
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            signal_type, sentiment_score, technical_score, 
            sentiment_data, market_data
        )
        
        return {
            'ticker': ticker,
            'signal_type': signal_type,
            'confidence': float(overall_confidence),
            'sentiment_score': float(sentiment_score),
            'technical_score': float(technical_score),
            'final_score': float(final_score),
            'reasoning': reasoning,
            'technical_indicators': market_data.get('indicators', {})
        }
    
    def _calculate_technical_score(self, market_data: Dict) -> float:
        """Calculate technical indicator score.
        
        Args:
            market_data: Dictionary with technical indicators
            
        Returns:
            Technical score from -1 (bearish) to 1 (bullish)
        """
        indicators = market_data.get('indicators', {})
        if not indicators:
            return 0.0
        
        scores = []
        
        # RSI (Relative Strength Index)
        rsi = indicators.get('RSI')
        if rsi is not None:
            if rsi < 30:  # Oversold - bullish
                scores.append(0.7)
            elif rsi > 70:  # Overbought - bearish
                scores.append(-0.7)
            elif rsi < 50:  # Below neutral - slightly bullish
                scores.append(0.2)
            else:  # Above neutral - slightly bearish
                scores.append(-0.2)
        
        # MACD
        macd = indicators.get('MACD')
        macd_signal = indicators.get('MACD_signal')
        macd_diff = indicators.get('MACD_diff')
        
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:  # Bullish crossover
                scores.append(0.5)
            else:  # Bearish
                scores.append(-0.3)
        
        if macd_diff is not None:
            if macd_diff > 0:
                scores.append(0.3)
            else:
                scores.append(-0.3)
        
        # Moving Averages
        ma_20 = indicators.get('MA_20')
        ma_50 = indicators.get('MA_50')
        ma_200 = indicators.get('MA_200')
        current_price = indicators.get('current_price')
        
        if all([ma_20, ma_50, current_price]):
            # Price above MA20 and MA20 above MA50 = bullish
            if current_price > ma_20 > ma_50:
                scores.append(0.6)
            # Price below MA20 and MA20 below MA50 = bearish
            elif current_price < ma_20 < ma_50:
                scores.append(-0.6)
            # Price between MAs = neutral
            else:
                scores.append(0.0)
        
        if ma_200 and current_price:
            if current_price > ma_200:
                scores.append(0.2)  # Above long-term trend
            else:
                scores.append(-0.2)  # Below long-term trend
        
        # Bollinger Bands
        bb_high = indicators.get('BB_high')
        bb_low = indicators.get('BB_low')
        bb_mid = indicators.get('BB_mid')
        
        if all([bb_high, bb_low, bb_mid, current_price]):
            if current_price <= bb_low:  # Oversold
                scores.append(0.5)
            elif current_price >= bb_high:  # Overbought
                scores.append(-0.5)
            else:
                scores.append(0.0)
        
        # Volume
        volume = indicators.get('volume')
        volume_sma = indicators.get('volume_sma')
        
        if volume and volume_sma:
            if volume > volume_sma * 1.5:  # High volume - could indicate strong move
                scores.append(0.2)
            elif volume < volume_sma * 0.5:  # Low volume - weak interest
                scores.append(-0.1)
        
        # Average all scores and normalize to -1 to 1
        if scores:
            avg_score = sum(scores) / len(scores)
            # Normalize to ensure it's between -1 and 1
            return max(-1.0, min(1.0, avg_score))
        
        return 0.0
    
    def _calculate_technical_confidence(self, market_data: Dict) -> float:
        """Calculate confidence in technical analysis.
        
        Args:
            market_data: Dictionary with technical indicators
            
        Returns:
            Confidence score from 0 to 1
        """
        indicators = market_data.get('indicators', {})
        if not indicators:
            return 0.3  # Low confidence if no indicators
        
        # Count available indicators
        available_indicators = sum([
            1 if indicators.get('RSI') is not None else 0,
            1 if indicators.get('MACD') is not None else 0,
            1 if indicators.get('MA_20') is not None else 0,
            1 if indicators.get('MA_50') is not None else 0,
            1 if indicators.get('MA_200') is not None else 0,
            1 if indicators.get('BB_high') is not None else 0
        ])
        
        # More indicators = higher confidence (up to a point)
        confidence = min(1.0, 0.4 + (available_indicators / 10.0))
        return confidence
    
    def _generate_reasoning(self, signal_type: str, sentiment_score: float,
                           technical_score: float, sentiment_data: Dict,
                           market_data: Dict) -> str:
        """Generate human-readable reasoning for the signal.
        
        Args:
            signal_type: buy, sell, or hold
            sentiment_score: Sentiment score (-1 to 1)
            technical_score: Technical score (-1 to 1)
            sentiment_data: Sentiment data dictionary
            market_data: Market data dictionary
            
        Returns:
            Reasoning string
        """
        sentiment_label = sentiment_data.get('overall_sentiment', 'neutral')
        sentiment_count = sentiment_data.get('total_count', 0)
        
        reasoning_parts = []
        
        # Sentiment reasoning
        if sentiment_count > 0:
            reasoning_parts.append(
                f"Sentiment analysis ({sentiment_count} mentions) shows "
                f"{sentiment_label} sentiment (score: {sentiment_score:.2f})"
            )
        else:
            reasoning_parts.append("Limited sentiment data available")
        
        # Technical reasoning
        indicators = market_data.get('indicators', {})
        tech_reasons = []
        
        rsi = indicators.get('RSI')
        if rsi:
            if rsi < 30:
                tech_reasons.append("RSI indicates oversold conditions")
            elif rsi > 70:
                tech_reasons.append("RSI indicates overbought conditions")
        
        macd_diff = indicators.get('MACD_diff')
        if macd_diff:
            if macd_diff > 0:
                tech_reasons.append("MACD shows bullish momentum")
            else:
                tech_reasons.append("MACD shows bearish momentum")
        
        current_price = indicators.get('current_price')
        ma_20 = indicators.get('MA_20')
        if current_price and ma_20:
            if current_price > ma_20:
                tech_reasons.append("Price is above 20-day moving average")
            else:
                tech_reasons.append("Price is below 20-day moving average")
        
        if tech_reasons:
            reasoning_parts.append("Technical indicators: " + ", ".join(tech_reasons[:3]))
        
        # Combine reasoning
        reasoning = ". ".join(reasoning_parts)
        
        # Add signal conclusion
        if signal_type == 'buy':
            reasoning += f". Combined score ({sentiment_score:.2f} sentiment + {technical_score:.2f} technical) suggests BUY signal."
        elif signal_type == 'sell':
            reasoning += f". Combined score ({sentiment_score:.2f} sentiment + {technical_score:.2f} technical) suggests SELL signal."
        else:
            reasoning += f". Combined score ({sentiment_score:.2f} sentiment + {technical_score:.2f} technical) suggests HOLD position."
        
        return reasoning
    
    def calculate_position_size(self, capital: float, signal_confidence: float,
                               volatility: Optional[float] = None,
                               risk_per_trade: float = 0.02) -> float:
        """Calculate position size based on confidence and risk.
        
        Args:
            capital: Available capital
            signal_confidence: Confidence in the signal (0-1)
            volatility: Optional volatility measure (standard deviation)
            risk_per_trade: Percentage of capital to risk per trade (default 2%)
            
        Returns:
            Position size in dollars
        """
        # Base position size on risk percentage
        base_position = capital * risk_per_trade
        
        # Adjust based on confidence
        # Higher confidence = larger position (up to 2x base)
        position_multiplier = 0.5 + (signal_confidence * 1.5)
        position_multiplier = min(2.0, max(0.5, position_multiplier))
        
        position_size = base_position * position_multiplier
        
        # Adjust for volatility if provided
        if volatility:
            # Higher volatility = smaller position
            volatility_adjustment = 1.0 / (1.0 + volatility)
            position_size *= volatility_adjustment
        
        return position_size

