"""Yahoo Finance integration for fetching market data."""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional, Dict
from datetime import datetime, timedelta
import ta


class MarketDataFetcher:
    """Fetches market data from Yahoo Finance."""
    
    def __init__(self):
        """Initialize the market data fetcher."""
        pass
    
    def get_historical_data(self, ticker: str, period: str = '1y', 
                           interval: str = '1d') -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance.
        
        Args:
            ticker: Stock ticker symbol
            period: Period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with dates, open, high, low, close, volume
        """
        try:
            stock = yf.Ticker(ticker.upper())
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                return pd.DataFrame()
            
            # Reset index to make Date a column
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'date'}, inplace=True)
            
            # Ensure date column is datetime
            df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Fetch latest price for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Current price, or None if error
        """
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            if current_price:
                return float(current_price)
            
            # Fallback: get last close price from recent data
            df = self.get_historical_data(ticker, period='5d')
            if not df.empty:
                return float(df['Close'].iloc[-1])
            
            return None
        except Exception as e:
            print(f"Error fetching current price for {ticker}: {e}")
            return None
    
    def get_market_indicators(self, ticker: str, period: str = '1y') -> Dict:
        """Calculate technical indicators for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            period: Period for historical data
            
        Returns:
            Dictionary with technical indicators (RSI, MACD, moving averages, etc.)
        """
        try:
            df = self.get_historical_data(ticker, period=period)
            
            if df.empty:
                return {}
            
            # Calculate RSI (Relative Strength Index)
            rsi = ta.momentum.RSIIndicator(close=df['Close'], window=14)
            df['RSI'] = rsi.rsi()
            
            # Calculate MACD (Moving Average Convergence Divergence)
            macd = ta.trend.MACD(close=df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            df['MACD_diff'] = macd.macd_diff()
            
            # Calculate Moving Averages
            df['MA_20'] = ta.trend.SMAIndicator(close=df['Close'], window=20).sma_indicator()
            df['MA_50'] = ta.trend.SMAIndicator(close=df['Close'], window=50).sma_indicator()
            df['MA_200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()
            
            # Calculate Bollinger Bands
            bollinger = ta.volatility.BollingerBands(close=df['Close'], window=20)
            df['BB_high'] = bollinger.bollinger_hband()
            df['BB_low'] = bollinger.bollinger_lband()
            df['BB_mid'] = bollinger.bollinger_mavg()
            
            # Calculate Volume indicators
            volume_sma = ta.volume.VolumeSMAIndicator(close=df['Close'], volume=df['Volume'], window=20)
            df['Volume_SMA'] = volume_sma.volume_sma()
            
            # Get latest values
            latest = df.iloc[-1]
            
            indicators = {
                'RSI': float(latest['RSI']) if pd.notna(latest['RSI']) else None,
                'MACD': float(latest['MACD']) if pd.notna(latest['MACD']) else None,
                'MACD_signal': float(latest['MACD_signal']) if pd.notna(latest['MACD_signal']) else None,
                'MACD_diff': float(latest['MACD_diff']) if pd.notna(latest['MACD_diff']) else None,
                'MA_20': float(latest['MA_20']) if pd.notna(latest['MA_20']) else None,
                'MA_50': float(latest['MA_50']) if pd.notna(latest['MA_50']) else None,
                'MA_200': float(latest['MA_200']) if pd.notna(latest['MA_200']) else None,
                'BB_high': float(latest['BB_high']) if pd.notna(latest['BB_high']) else None,
                'BB_low': float(latest['BB_low']) if pd.notna(latest['BB_low']) else None,
                'BB_mid': float(latest['BB_mid']) if pd.notna(latest['BB_mid']) else None,
                'current_price': float(latest['Close']) if pd.notna(latest['Close']) else None,
                'volume': int(latest['Volume']) if pd.notna(latest['Volume']) else None,
                'volume_sma': float(latest['Volume_SMA']) if pd.notna(latest['Volume_SMA']) else None
            }
            
            # Add indicators to dataframe for full history
            indicators['full_data'] = df.to_dict('records')
            
            return indicators
        except Exception as e:
            print(f"Error calculating indicators for {ticker}: {e}")
            return {}
    
    def get_sp500_data(self, period: str = '1y') -> pd.DataFrame:
        """Fetch S&P 500 index data for benchmark comparison.
        
        Args:
            period: Period to fetch
            
        Returns:
            DataFrame with S&P 500 OHLCV data
        """
        try:
            sp500 = yf.Ticker('^GSPC')
            df = sp500.history(period=period)
            
            if df.empty:
                return pd.DataFrame()
            
            # Reset index to make Date a column
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'date'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error fetching S&P 500 data: {e}")
            return pd.DataFrame()
    
    def get_ticker_info(self, ticker: str) -> Dict:
        """Get general information about a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with ticker information
        """
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            return {
                'symbol': info.get('symbol', ticker.upper()),
                'name': info.get('longName') or info.get('shortName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap'),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'previous_close': info.get('previousClose'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow'),
                'volume': info.get('volume'),
                'average_volume': info.get('averageVolume')
            }
        except Exception as e:
            print(f"Error fetching ticker info for {ticker}: {e}")
            return {}

