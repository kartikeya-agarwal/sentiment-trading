"""Backtesting engine for evaluating trading strategies."""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
from .trading_strategy import SentimentTradingStrategy
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data.yahoo_finance import MarketDataFetcher
from database.db_manager import DatabaseManager


class BacktestingEngine:
    """Backtesting engine for trading strategies."""
    
    def __init__(self, initial_capital: float = 100000, transaction_cost: float = 0.001):
        """Initialize backtesting engine.
        
        Args:
            initial_capital: Starting capital for backtesting
            transaction_cost: Transaction cost as percentage (e.g., 0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.market_fetcher = MarketDataFetcher()
    
    def run_backtest(self, strategy: SentimentTradingStrategy, ticker: str,
                    start_date: datetime, end_date: datetime,
                    sentiment_data_fn: Optional[callable] = None,
                    db_manager: Optional[DatabaseManager] = None) -> Dict:
        """Run backtest on historical data.
        
        Args:
            strategy: Trading strategy instance
            ticker: Stock ticker symbol
            start_date: Start date for backtest
            end_date: End date for backtest
            sentiment_data_fn: Optional function to get historical sentiment data
            db_manager: Optional database manager for sentiment data
            
        Returns:
            Dictionary with backtest results and performance metrics
        """
        # Load historical market data
        period = self._calculate_period(start_date, end_date)
        market_df = self.market_fetcher.get_historical_data(ticker, period=period, interval='1d')
        
        if market_df.empty:
            return {
                'error': 'No market data available for the specified period',
                'ticker': ticker
            }
        
        # Filter by date range
        market_df['date'] = pd.to_datetime(market_df['date'])
        market_df = market_df[(market_df['date'] >= start_date) & 
                             (market_df['date'] <= end_date)].copy()
        
        if market_df.empty:
            return {
                'error': 'No market data in the specified date range',
                'ticker': ticker
            }
        
        market_df = market_df.sort_values('date').reset_index(drop=True)
        
        # Load historical sentiment data
        if db_manager:
            sentiment_df = db_manager.get_historical_sentiment(ticker, start_date, end_date)
        elif sentiment_data_fn:
            sentiment_df = sentiment_data_fn(ticker, start_date, end_date)
        else:
            sentiment_df = pd.DataFrame()
        
        # Initialize portfolio
        portfolio = {
            'cash': self.initial_capital,
            'shares': 0,
            'positions': []
        }
        
        daily_values = []
        daily_returns = []
        trades = []
        
        # Run backtest day by day
        for idx, row in market_df.iterrows():
            current_date = row['date']
            current_price = row['Close']
            
            # Get sentiment for this date (use most recent available)
            if not sentiment_df.empty:
                sentiment_up_to_date = sentiment_df[sentiment_df['date'] <= current_date]
                if not sentiment_up_to_date.empty:
                    latest_sentiment = sentiment_up_to_date.iloc[-1]
                    sentiment_data = {
                        'weighted_score': latest_sentiment.get('avg_sentiment_score', 0.0),
                        'confidence': latest_sentiment.get('avg_confidence', 0.5),
                        'total_count': latest_sentiment.get('mention_count', 0),
                        'overall_sentiment': 'neutral'
                    }
                else:
                    sentiment_data = {'weighted_score': 0.0, 'confidence': 0.3, 
                                    'total_count': 0, 'overall_sentiment': 'neutral'}
            else:
                sentiment_data = {'weighted_score': 0.0, 'confidence': 0.3,
                                'total_count': 0, 'overall_sentiment': 'neutral'}
            
            # Get technical indicators for this date
            # Calculate indicators from historical data up to this point
            market_data_up_to_date = market_df[market_df['date'] <= current_date].copy()
            
            if len(market_data_up_to_date) >= 20:  # Need enough data for indicators
                indicators = self._calculate_indicators_for_date(market_data_up_to_date, current_price)
            else:
                indicators = {}
            
            market_data = {
                'indicators': indicators,
                'current_price': current_price
            }
            
            # Generate signal
            signal = strategy.generate_signal(ticker, sentiment_data, market_data)
            
            # Execute trades based on signal
            if signal['signal_type'] == 'buy' and portfolio['cash'] > 0:
                # Calculate position size
                position_value = strategy.calculate_position_size(
                    portfolio['cash'],
                    signal['confidence']
                )
                
                shares_to_buy = int(position_value / current_price)
                if shares_to_buy > 0:
                    cost = shares_to_buy * current_price * (1 + self.transaction_cost)
                    
                    if cost <= portfolio['cash']:
                        portfolio['cash'] -= cost
                        portfolio['shares'] += shares_to_buy
                        
                        trades.append({
                            'date': current_date,
                            'type': 'buy',
                            'shares': shares_to_buy,
                            'price': current_price,
                            'cost': cost
                        })
            
            elif signal['signal_type'] == 'sell' and portfolio['shares'] > 0:
                # Sell all shares
                shares_to_sell = portfolio['shares']
                revenue = shares_to_sell * current_price * (1 - self.transaction_cost)
                
                portfolio['cash'] += revenue
                portfolio['shares'] = 0
                
                trades.append({
                    'date': current_date,
                    'type': 'sell',
                    'shares': shares_to_sell,
                    'price': current_price,
                    'revenue': revenue
                })
            
            # Calculate portfolio value
            portfolio_value = portfolio['cash'] + (portfolio['shares'] * current_price)
            daily_values.append({
                'date': current_date,
                'value': portfolio_value,
                'cash': portfolio['cash'],
                'shares': portfolio['shares'],
                'price': current_price
            })
        
        # Calculate daily returns
        df_values = pd.DataFrame(daily_values)
        if len(df_values) > 1:
            df_values['daily_return'] = df_values['value'].pct_change()
            daily_returns = df_values['daily_return'].dropna().tolist()
        else:
            daily_returns = [0.0]
        
        # Calculate final value
        final_row = df_values.iloc[-1]
        final_value = final_row['value']
        final_price = final_row['price']
        
        # Calculate performance metrics
        total_return = ((final_value - self.initial_capital) / self.initial_capital) * 100
        
        # Sharpe ratio (assuming 252 trading days per year)
        if len(daily_returns) > 1 and np.std(daily_returns) > 0:
            sharpe_ratio = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
        
        # Maximum drawdown
        if len(df_values) > 0:
            cumulative = (1 + df_values['daily_return']).cumprod()
            running_max = cumulative.cummax()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = float(drawdown.min()) * 100
        else:
            max_drawdown = 0.0
        
        # Win rate (for trades)
        if len(trades) >= 2:
            # Simple win rate calculation based on profitable exits
            profitable_trades = 0
            total_sell_trades = 0
            buy_prices = {}
            
            for trade in trades:
                if trade['type'] == 'buy':
                    buy_prices[trade['date']] = trade['price']
                elif trade['type'] == 'sell':
                    total_sell_trades += 1
                    # Find corresponding buy price (simplified - uses most recent buy)
                    if buy_prices:
                        last_buy_price = list(buy_prices.values())[-1]
                        if trade['price'] > last_buy_price:
                            profitable_trades += 1
            
            win_rate = (profitable_trades / total_sell_trades * 100) if total_sell_trades > 0 else 0.0
        else:
            win_rate = 0.0
        
        # Compare with S&P 500
        sp500_df = self.market_fetcher.get_sp500_data(period=period)
        sp500_performance = 0.0
        
        if not sp500_df.empty:
            sp500_df['date'] = pd.to_datetime(sp500_df['date'])
            sp500_df = sp500_df[(sp500_df['date'] >= start_date) & 
                               (sp500_df['date'] <= end_date)].copy()
            
            if not sp500_df.empty and len(sp500_df) > 1:
                sp500_start = sp500_df.iloc[0]['Close']
                sp500_end = sp500_df.iloc[-1]['Close']
                sp500_return = ((sp500_end - sp500_start) / sp500_start) * 100
                sp500_performance = sp500_return
        
        vs_sp500 = total_return - sp500_performance
        
        return {
            'ticker': ticker,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_value': float(final_value),
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'vs_sp500_performance': float(vs_sp500),
            'sp500_return': float(sp500_performance),
            'daily_returns': daily_returns,
            'daily_values': [{'date': v['date'].isoformat(), 'value': v['value']} 
                           for v in daily_values],
            'trades': [{'date': t['date'].isoformat(), 'type': t['type'], 
                       'shares': t['shares'], 'price': t['price']} 
                      for t in trades],
            'total_trades': len(trades)
        }
    
    def _calculate_period(self, start_date: datetime, end_date: datetime) -> str:
        """Calculate period string for yfinance based on date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Period string for yfinance
        """
        days = (end_date - start_date).days
        
        if days <= 5:
            return '5d'
        elif days <= 30:
            return '1mo'
        elif days <= 90:
            return '3mo'
        elif days <= 180:
            return '6mo'
        elif days <= 365:
            return '1y'
        elif days <= 730:
            return '2y'
        else:
            return 'max'
    
    def _calculate_indicators_for_date(self, market_df: pd.DataFrame, current_price: float) -> Dict:
        """Calculate technical indicators up to a specific date.
        
        Args:
            market_df: Historical market data up to the date
            current_price: Current price
            
        Returns:
            Dictionary with technical indicators
        """
        try:
            import ta
            
            df = market_df.copy()
            
            # Calculate RSI
            if len(df) >= 14:
                rsi = ta.momentum.RSIIndicator(close=df['Close'], window=14)
                rsi_value = rsi.rsi().iloc[-1] if pd.notna(rsi.rsi().iloc[-1]) else None
            else:
                rsi_value = None
            
            # Calculate MACD
            if len(df) >= 26:
                macd = ta.trend.MACD(close=df['Close'])
                macd_value = macd.macd().iloc[-1] if pd.notna(macd.macd().iloc[-1]) else None
                macd_signal = macd.macd_signal().iloc[-1] if pd.notna(macd.macd_signal().iloc[-1]) else None
                macd_diff = macd.macd_diff().iloc[-1] if pd.notna(macd.macd_diff().iloc[-1]) else None
            else:
                macd_value = None
                macd_signal = None
                macd_diff = None
            
            # Calculate Moving Averages
            ma_20 = ta.trend.SMAIndicator(close=df['Close'], window=20).sma_indicator().iloc[-1] if len(df) >= 20 else None
            ma_50 = ta.trend.SMAIndicator(close=df['Close'], window=50).sma_indicator().iloc[-1] if len(df) >= 50 else None
            ma_200 = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator().iloc[-1] if len(df) >= 200 else None
            
            # Bollinger Bands
            if len(df) >= 20:
                bb = ta.volatility.BollingerBands(close=df['Close'], window=20)
                bb_high = bb.bollinger_hband().iloc[-1] if pd.notna(bb.bollinger_hband().iloc[-1]) else None
                bb_low = bb.bollinger_lband().iloc[-1] if pd.notna(bb.bollinger_lband().iloc[-1]) else None
                bb_mid = bb.bollinger_mavg().iloc[-1] if pd.notna(bb.bollinger_mavg().iloc[-1]) else None
            else:
                bb_high = None
                bb_low = None
                bb_mid = None
            
            # Volume
            volume = df['Volume'].iloc[-1] if len(df) > 0 else None
            volume_sma = ta.volume.VolumeSMAIndicator(close=df['Close'], volume=df['Volume'], window=20).volume_sma().iloc[-1] if len(df) >= 20 else None
            
            return {
                'RSI': float(rsi_value) if rsi_value is not None else None,
                'MACD': float(macd_value) if macd_value is not None else None,
                'MACD_signal': float(macd_signal) if macd_signal is not None else None,
                'MACD_diff': float(macd_diff) if macd_diff is not None else None,
                'MA_20': float(ma_20) if ma_20 is not None else None,
                'MA_50': float(ma_50) if ma_50 is not None else None,
                'MA_200': float(ma_200) if ma_200 is not None else None,
                'BB_high': float(bb_high) if bb_high is not None else None,
                'BB_low': float(bb_low) if bb_low is not None else None,
                'BB_mid': float(bb_mid) if bb_mid is not None else None,
                'current_price': float(current_price),
                'volume': int(volume) if volume is not None else None,
                'volume_sma': float(volume_sma) if volume_sma is not None else None
            }
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return {}

