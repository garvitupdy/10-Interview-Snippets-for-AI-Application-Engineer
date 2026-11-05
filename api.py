"""
Snippet: Resilient API Wrapper with Exponential Backoff and Jitter
Difficulty: Advanced

Interview Context:
Production AI applications rely heavily on external LLM APIs (OpenAI, Anthropic) that frequently experience transient network glitches, load shedding, and strict rate limits (HTTP 429). Interviewers ask for this to evaluate your understanding of distributed systems resilience, specifically how to prevent the "thundering herd" problem using randomized jitter and how to handle non-retryable client errors gracefully.
"""

import time
import random
import functools
import logging
import requests
from typing import Callable, Any

# Configure logging for production observability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResilientAPIWrapper")

class RateLimitError(Exception):
    """Custom exception raised when rate limits are exhausted."""
    pass

class NonRetryableError(Exception):
    """Raised for client-side errors (e.g., 400 Bad Request, 401 Unauthorized) where retrying is futile."""
    pass

def resilient_api_call(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
):
    """
    A production-grade decorator that adds exponential backoff, full jitter, 
    timeout management, and smart status-code filtering to any API call.
    """
    def decorator(func: Callable[..., requests.Response]) -> Callable[..., requests.Response]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> requests.Response:
            attempt = 0
            
            while attempt < max_retries:
                try:
                    # Execute the underlying network call
                    response = func(*args, **kwargs)
                    
                    # 1. Handle Successful Responses
                    if response.status_code < 400:
                        return response
                    
                    # 2. Handle Rate Limits (HTTP 429) & Server Errors (HTTP 5xx)
                    if response.status_code == 429 or 500 <= response.status_code < 600:
                        attempt += 1
                        if attempt >= max_retries:
                            raise RateLimitError(f"Max retries ({max_retries}) exceeded due to status {response.status_code}.")
                        
                        # Respect the 'Retry-After' header if provided by the API provider
                        retry_after = response.headers.get("Retry-After")
                        if retry_after is not None and retry_after.isdigit():
                            sleep_time = float(retry_after)
                            logger.warning(f"API rate limited (429). Respecting server Retry-After header: {sleep_time}s")
                        else:
                            # Exponential Backoff with Full Jitter
                            # Formula: sleep = random_uniform(0, min(max_delay, base_delay * (backoff_factor ** attempt)))
                            # Why Jitter? If 1000 concurrent worker instances hit a rate limit and retry 
                            # at the exact same intervals, they create synchronized traffic spikes (thundering herd). 
                            # Jitter randomizes the backoff to smooth out the load.
                            exponential_delay = base_delay * (backoff_factor ** attempt)
                            capped_delay = min(max_delay, exponential_delay)
                            sleep_time = random.uniform(0, capped_delay)
                            
                            logger.warning(
                                f"Transient error {response.status_code} encountered. "
                                f"Retrying attempt {attempt}/{max_retries} in {sleep_time:.2f} seconds..."
                            )
                        
                        time.sleep(sleep_time)
                        continue
                    
                    # 3. Handle Non-Retryable Client Errors (HTTP 400, 401, 403, 404, etc.)
                    # Fail fast! Retrying a malformed prompt (400) or invalid token (401) wastes resources.
                    elif 400 <= response.status_code < 500:
                        raise NonRetryableError(
                            f"Client error {response.status_code}: {response.text}. Aborting retries."
                        )
                        
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    # 4. Handle Network-Level Transient Failures (DNS lookups, dropped TCP connections, timeouts)
                    attempt += 1
                    if attempt >= max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded due to network failure: {e}")
                        raise
                    
                    # Apply backoff for network drops as well
                    exponential_delay = base_delay * (backoff_factor ** attempt)
                    sleep_time = random.uniform(0, min(max_delay, exponential_delay))
                    
                    logger.warning(
                        f"Network exception ({type(e).__name__}) caught. "
                        f"Retrying attempt {attempt}/{max_retries} in {sleep_time:.2f} seconds..."
                    )
                    time.sleep(sleep_time)
                    
            raise RuntimeError("Unexpected exit from retry loop.")
        return wrapper
    return decorator

# --- Example Usage & Verification ---

# A mock function simulating an unstable API endpoint
class MockAPIServer:
    def __init__(self):
        self.call_count = 0

    @resilient_api_call(max_retries=3, base_delay=0.1, max_delay=1.0)
    def call_llm_endpoint(self, payload: dict) -> requests.Response:
        self.call_count += 1
        
        # Simulate transient failure on attempt 1
        if self.call_count == 1:
            mock_res = requests.Response()
            mock_res.status_code = 429
            mock_res.headers["Retry-After"] = "0.2"
            return mock_res
            
        # Simulate server crash on attempt 2
        if self.call_count == 2:
            mock_res = requests.Response()
            mock_res.status_code = 503
            return mock_res
            
        # Succeed on attempt 3
        mock_res = requests.Response()
        mock_res.status_code = 200
        mock_res._content = b'{"choices": [{"text": "Hello, resilient world!"}]}'
        return mock_res

if __name__ == "__main__":
    server = MockAPIServer()
    
    print("Executing resilient API wrapper test...")
    response = server.call_llm_endpoint({"prompt": "Hello"})
    
    print(f"Final Status Code: {response.status_code}")
    print(f"Final Response Content: {response.text}")
    print(f"Total attempts made: {server.call_count}")
    
    # Sanity Checks
    assert response.status_code == 200, "API call should have eventually succeeded."
    assert server.call_count == 3, "Should have taken exactly 3 attempts."
    
    print("\nImplementation successful: Wrapper successfully navigated 429 and 503 errors using backoff and retry logic.")
