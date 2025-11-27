"""Database models for sentiment and market data storage."""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class SentimentData(Base):
    """Model for storing sentiment analysis results."""
    __tablename__ = 'sentiment_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # reddit, twitter, news
    text = Column(Text, nullable=False)
    sentiment_score = Column(Float, nullable=False)  # -1 to 1
    sentiment_label = Column(String(20), nullable=False)  # positive, negative, neutral
    confidence = Column(Float, default=0.0)  # 0 to 1
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    raw_data = Column(JSON)  # Store original API response
    metadata = Column(JSON)  # Additional metadata (upvotes, retweets, etc.)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'source': self.source,
            'text': self.text,
            'sentiment_score': self.sentiment_score,
            'sentiment_label': self.sentiment_label,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'raw_data': self.raw_data,
            'metadata': self.metadata
        }


class MarketData(Base):
    """Model for storing market/OHLCV data."""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    indicators = Column(JSON)  # RSI, MACD, moving averages, etc.
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'date': self.date.isoformat() if self.date else None,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'indicators': self.indicators
        }


class TradingSignal(Base):
    """Model for storing trading signals."""
    __tablename__ = 'trading_signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)  # buy, sell, hold
    confidence = Column(Float, nullable=False)  # 0 to 1
    sentiment_score = Column(Float, nullable=False)
    technical_indicators = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    reasoning = Column(Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'sentiment_score': self.sentiment_score,
            'technical_indicators': self.technical_indicators,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'reasoning': self.reasoning
        }


class BacktestResult(Base):
    """Model for storing backtesting results."""
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(100), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_value = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)  # Percentage
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    vs_sp500_performance = Column(Float)  # Percentage difference
    daily_returns = Column(JSON)  # Array of daily returns
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'ticker': self.ticker,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'initial_capital': self.initial_capital,
            'final_value': self.final_value,
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'vs_sp500_performance': self.vs_sp500_performance,
            'daily_returns': self.daily_returns,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

