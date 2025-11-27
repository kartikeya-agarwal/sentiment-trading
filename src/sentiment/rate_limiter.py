"""Rate limiting and cost control for API calls."""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import json
import os


class RateLimiter:
    """Rate limiter with cost tracking for API calls."""
    
    def __init__(self, max_requests_per_minute: int = 60, 
                 max_requests_per_day: int = 1000,
                 max_daily_cost: float = 10.0,
                 cost_per_1k_tokens: float = 0.15):
        """Initialize rate limiter.
        
        Args:
            max_requests_per_minute: Maximum API requests per minute
            max_requests_per_day: Maximum API requests per day
            max_daily_cost: Maximum daily cost in USD
            cost_per_1k_tokens: Cost per 1k tokens (for GPT-4o-mini input: $0.15/1M tokens)
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_day = max_requests_per_day
        self.max_daily_cost = max_daily_cost
        self.cost_per_1k_tokens = cost_per_1k_tokens / 1000  # Convert to per 1k tokens
        
        # Track requests
        self.requests_timestamps = []
        self.daily_requests = defaultdict(int)
        self.daily_costs = defaultdict(float)
        self.last_reset_date = datetime.now().date()
        
        # Load saved state if exists
        self._load_state()
    
    def _load_state(self):
        """Load rate limit state from file."""
        state_file = 'rate_limit_state.json'
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.daily_requests = {k: int(v) for k, v in state.get('daily_requests', {}).items()}
                    self.daily_costs = {k: float(v) for k, v in state.get('daily_costs', {}).items()}
            except Exception as e:
                print(f"Error loading rate limit state: {e}")
    
    def _save_state(self):
        """Save rate limit state to file."""
        state_file = 'rate_limit_state.json'
        try:
            state = {
                'daily_requests': dict(self.daily_requests),
                'daily_costs': dict(self.daily_costs)
            }
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Error saving rate limit state: {e}")
    
    def _reset_if_new_day(self):
        """Reset daily counters if it's a new day."""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.last_reset_date = today
            # Clear old data (keep last 7 days)
            cutoff_date = (today - timedelta(days=7)).isoformat()
            self.daily_requests = {k: v for k, v in self.daily_requests.items() 
                                  if k >= cutoff_date}
            self.daily_costs = {k: v for k, v in self.daily_costs.items() 
                               if k >= cutoff_date}
    
    def _clean_old_timestamps(self):
        """Remove timestamps older than 1 minute."""
        now = time.time()
        one_minute_ago = now - 60
        self.requests_timestamps = [ts for ts in self.requests_timestamps if ts > one_minute_ago]
    
    def check_rate_limit(self) -> tuple[bool, Optional[str]]:
        """Check if request is allowed.
        
        Returns:
            Tuple of (allowed, error_message)
        """
        self._reset_if_new_day()
        self._clean_old_timestamps()
        
        # Check per-minute limit
        if len(self.requests_timestamps) >= self.max_requests_per_minute:
            return False, f"Rate limit exceeded: {self.max_requests_per_minute} requests per minute"
        
        # Check per-day limit
        today = datetime.now().date().isoformat()
        if self.daily_requests[today] >= self.max_requests_per_day:
            return False, f"Daily limit exceeded: {self.max_requests_per_day} requests per day"
        
        # Check daily cost limit
        if self.daily_costs[today] >= self.max_daily_cost:
            return False, f"Daily cost limit exceeded: ${self.max_daily_cost:.2f} USD per day"
        
        return True, None
    
    def record_request(self, estimated_tokens: int = 500):
        """Record an API request.
        
        Args:
            estimated_tokens: Estimated number of tokens used
        """
        self._reset_if_new_day()
        
        # Record timestamp
        self.requests_timestamps.append(time.time())
        
        # Record daily request
        today = datetime.now().date().isoformat()
        self.daily_requests[today] += 1
        
        # Estimate and record cost (tokens to cost conversion)
        # GPT-4o-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens
        # We estimate 70% input, 30% output tokens
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)
        input_cost = (input_tokens / 1_000_000) * 0.15
        output_cost = (output_tokens / 1_000_000) * 0.60
        estimated_cost = input_cost + output_cost
        self.daily_costs[today] += estimated_cost
        
        # Save state
        self._save_state()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        self._clean_old_timestamps()
        
        if len(self.requests_timestamps) >= self.max_requests_per_minute:
            # Wait until oldest request is 1 minute old
            if self.requests_timestamps:
                oldest = min(self.requests_timestamps)
                wait_time = 60 - (time.time() - oldest) + 1
                if wait_time > 0:
                    time.sleep(wait_time)
    
    def get_stats(self) -> Dict:
        """Get current rate limit statistics.
        
        Returns:
            Dictionary with stats
        """
        self._reset_if_new_day()
        today = datetime.now().date().isoformat()
        
        return {
            'requests_last_minute': len(self.requests_timestamps),
            'max_requests_per_minute': self.max_requests_per_minute,
            'requests_today': self.daily_requests.get(today, 0),
            'max_requests_per_day': self.max_requests_per_day,
            'cost_today': round(self.daily_costs.get(today, 0.0), 4),
            'max_daily_cost': self.max_daily_cost,
            'remaining_daily_budget': round(self.max_daily_cost - self.daily_costs.get(today, 0.0), 4)
        }


class CostTracker:
    """Track API costs."""
    
    def __init__(self):
        """Initialize cost tracker."""
        self.daily_costs = defaultdict(float)
        self.last_reset_date = datetime.now().date()
        self._load_costs()
    
    def _load_costs(self):
        """Load cost data from file."""
        cost_file = 'cost_tracker.json'
        if os.path.exists(cost_file):
            try:
                with open(cost_file, 'r') as f:
                    data = json.load(f)
                    self.daily_costs = {k: float(v) for k, v in data.items()}
            except Exception as e:
                print(f"Error loading cost data: {e}")
    
    def _save_costs(self):
        """Save cost data to file."""
        cost_file = 'cost_tracker.json'
        try:
            # Keep only last 30 days
            cutoff_date = (datetime.now().date() - timedelta(days=30)).isoformat()
            filtered_costs = {k: v for k, v in self.daily_costs.items() if k >= cutoff_date}
            
            with open(cost_file, 'w') as f:
                json.dump(filtered_costs, f, indent=2)
        except Exception as e:
            print(f"Error saving cost data: {e}")
    
    def add_cost(self, amount: float):
        """Add cost for today.
        
        Args:
            amount: Cost in USD
        """
        today = datetime.now().date().isoformat()
        self.daily_costs[today] += amount
        self._save_costs()
    
    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """Get cost for a specific date.
        
        Args:
            date: Date to check (default: today)
            
        Returns:
            Cost in USD
        """
        if date is None:
            date = datetime.now().date()
        return self.daily_costs.get(date.isoformat(), 0.0)
    
    def get_total_cost(self, days: int = 30) -> float:
        """Get total cost for last N days.
        
        Args:
            days: Number of days to include
            
        Returns:
            Total cost in USD
        """
        cutoff_date = (datetime.now().date() - timedelta(days=days)).isoformat()
        return sum(v for k, v in self.daily_costs.items() if k >= cutoff_date)
    
    def get_stats(self) -> Dict:
        """Get cost statistics.
        
        Returns:
            Dictionary with cost stats
        """
        today = datetime.now().date().isoformat()
        return {
            'cost_today': round(self.daily_costs.get(today, 0.0), 4),
            'cost_this_week': round(self.get_total_cost(days=7), 4),
            'cost_this_month': round(self.get_total_cost(days=30), 4)
        }

