"""Database manager for handling database operations."""

import os
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Optional
from .models import Base, SentimentData, MarketData, TradingSignal, BacktestResult


class DatabaseManager:
    """Manages database operations for sentiment and market data."""
    
    def __init__(self, db_path: str = 'sentiment_trading.db'):
        """Initialize database connection and create tables if they don't exist.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def save_sentiment_data(self, data: Dict) -> Optional[int]:
        """Save sentiment data to database.
        
        Args:
            data: Dictionary containing sentiment data fields
            
        Returns:
            ID of inserted record, or None if error
        """
        session = self.get_session()
        try:
            sentiment = SentimentData(
                ticker=data.get('ticker'),
                source=data.get('source'),
                text=data.get('text'),
                sentiment_score=data.get('sentiment_score', 0.0),
                sentiment_label=data.get('sentiment_label', 'neutral'),
                confidence=data.get('confidence', 0.0),
                timestamp=data.get('timestamp', datetime.utcnow()),
                raw_data=data.get('raw_data'),
                metadata=data.get('metadata')
            )
            session.add(sentiment)
            session.commit()
            record_id = sentiment.id
            session.close()
            return record_id
        except IntegrityError as e:
            session.rollback()
            session.close()
            print(f"Error saving sentiment data: {e}")
            return None
        except Exception as e:
            session.rollback()
            session.close()
            print(f"Unexpected error saving sentiment data: {e}")
            return None
    
    def save_market_data(self, data: Dict) -> Optional[int]:
        """Save or update market data (upsert by ticker+date).
        
        Args:
            data: Dictionary containing market data fields
            
        Returns:
            ID of inserted/updated record, or None if error
        """
        session = self.get_session()
        try:
            # Check if record exists
            existing = session.query(MarketData).filter(
                and_(
                    MarketData.ticker == data.get('ticker'),
                    MarketData.date == data.get('date')
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.open = data.get('open', existing.open)
                existing.high = data.get('high', existing.high)
                existing.low = data.get('low', existing.low)
                existing.close = data.get('close', existing.close)
                existing.volume = data.get('volume', existing.volume)
                if data.get('indicators'):
                    existing.indicators = data.get('indicators')
                session.commit()
                record_id = existing.id
            else:
                # Insert new record
                market = MarketData(
                    ticker=data.get('ticker'),
                    date=data.get('date'),
                    open=data.get('open'),
                    high=data.get('high'),
                    low=data.get('low'),
                    close=data.get('close'),
                    volume=data.get('volume'),
                    indicators=data.get('indicators')
                )
                session.add(market)
                session.commit()
                record_id = market.id
            
            session.close()
            return record_id
        except Exception as e:
            session.rollback()
            session.close()
            print(f"Error saving market data: {e}")
            return None
    
    def get_historical_sentiment(self, ticker: str, start_date: datetime, 
                                  end_date: datetime) -> pd.DataFrame:
        """Get historical sentiment data for a ticker within date range.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for query
            end_date: End date for query
            
        Returns:
            DataFrame with aggregated daily sentiment data
        """
        session = self.get_session()
        try:
            results = session.query(SentimentData).filter(
                and_(
                    SentimentData.ticker == ticker.upper(),
                    SentimentData.timestamp >= start_date,
                    SentimentData.timestamp <= end_date
                )
            ).all()
            session.close()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to list of dicts
            data = [r.to_dict() for r in results]
            df = pd.DataFrame(data)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Group by date and aggregate
            df['date'] = df['timestamp'].dt.date
            daily_agg = df.groupby('date').agg({
                'sentiment_score': ['mean', 'count'],
                'confidence': 'mean',
                'sentiment_label': lambda x: x.value_counts().to_dict()
            }).reset_index()
            
            daily_agg.columns = ['date', 'avg_sentiment_score', 'mention_count', 
                                'avg_confidence', 'sentiment_distribution']
            daily_agg['date'] = pd.to_datetime(daily_agg['date'])
            
            return daily_agg
        except Exception as e:
            session.close()
            print(f"Error getting historical sentiment: {e}")
            return pd.DataFrame()
    
    def get_historical_market_data(self, ticker: str, start_date: datetime, 
                                    end_date: datetime) -> pd.DataFrame:
        """Get historical market data for a ticker within date range.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for query
            end_date: End date for query
            
        Returns:
            DataFrame with OHLCV data
        """
        session = self.get_session()
        try:
            results = session.query(MarketData).filter(
                and_(
                    MarketData.ticker == ticker.upper(),
                    MarketData.date >= start_date,
                    MarketData.date <= end_date
                )
            ).order_by(MarketData.date).all()
            session.close()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to list of dicts
            data = [r.to_dict() for r in results]
            df = pd.DataFrame(data)
            
            # Convert date to datetime and set as index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
        except Exception as e:
            session.close()
            print(f"Error getting historical market data: {e}")
            return pd.DataFrame()
    
    def save_trading_signal(self, signal: Dict) -> Optional[int]:
        """Save a trading signal to database.
        
        Args:
            signal: Dictionary containing signal data
            
        Returns:
            ID of inserted record, or None if error
        """
        session = self.get_session()
        try:
            trading_signal = TradingSignal(
                ticker=signal.get('ticker'),
                signal_type=signal.get('signal_type'),
                confidence=signal.get('confidence'),
                sentiment_score=signal.get('sentiment_score'),
                technical_indicators=signal.get('technical_indicators'),
                timestamp=signal.get('timestamp', datetime.utcnow()),
                reasoning=signal.get('reasoning')
            )
            session.add(trading_signal)
            session.commit()
            record_id = trading_signal.id
            session.close()
            return record_id
        except Exception as e:
            session.rollback()
            session.close()
            print(f"Error saving trading signal: {e}")
            return None
    
    def save_backtest_result(self, result: Dict) -> Optional[int]:
        """Save backtest result to database.
        
        Args:
            result: Dictionary containing backtest result data
            
        Returns:
            ID of inserted record, or None if error
        """
        session = self.get_session()
        try:
            backtest = BacktestResult(
                strategy_name=result.get('strategy_name'),
                ticker=result.get('ticker'),
                start_date=result.get('start_date'),
                end_date=result.get('end_date'),
                initial_capital=result.get('initial_capital'),
                final_value=result.get('final_value'),
                total_return=result.get('total_return'),
                sharpe_ratio=result.get('sharpe_ratio'),
                max_drawdown=result.get('max_drawdown'),
                win_rate=result.get('win_rate'),
                vs_sp500_performance=result.get('vs_sp500_performance'),
                daily_returns=result.get('daily_returns')
            )
            session.add(backtest)
            session.commit()
            record_id = backtest.id
            session.close()
            return record_id
        except Exception as e:
            session.rollback()
            session.close()
            print(f"Error saving backtest result: {e}")
            return None
    
    def get_recent_sentiment_snippets(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Get recent sentiment snippets for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of snippets to return
            
        Returns:
            List of sentiment data dictionaries
        """
        session = self.get_session()
        try:
            results = session.query(SentimentData).filter(
                SentimentData.ticker == ticker.upper()
            ).order_by(SentimentData.timestamp.desc()).limit(limit).all()
            session.close()
            
            return [r.to_dict() for r in results]
        except Exception as e:
            session.close()
            print(f"Error getting recent sentiment snippets: {e}")
            return []

