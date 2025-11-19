"""Rate limiter to prevent hitting OpenRouter rate limits."""
import time
from threading import Lock

class RateLimiter:
    """Simple rate limiter to space out API requests."""
    
    def __init__(self, min_delay_seconds: float = 2.0):
        """
        Initialize rate limiter.
        
        Args:
            min_delay_seconds: Minimum seconds between requests
        """
        self.min_delay = min_delay_seconds
        self.last_request_time = 0
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to maintain rate limit."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last
                print(f"[RATE_LIMITER] Waiting {wait_time:.1f}s to avoid rate limits...")
                time.sleep(wait_time)
            
            self.last_request_time = time.time()

# Global rate limiter instance
_rate_limiter = RateLimiter(min_delay_seconds=5.0)  # 5 seconds between requests (increased rate)

def wait_for_rate_limit():
    """Wait if necessary to maintain rate limit."""
    _rate_limiter.wait_if_needed()

