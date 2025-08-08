# tools/youtube_search_tool.py (Minimal Fix)
import requests
import re
import time
from langchain.tools import tool

# Add basic rate limiting
_last_request_time = 0
_rate_limit_delay = 1

def search_youtube_scrape(query: str) -> str:
    global _last_request_time
    
    # Basic rate limiting
    current_time = time.time()
    if current_time - _last_request_time < _rate_limit_delay:
        time.sleep(_rate_limit_delay - (current_time - _last_request_time))
    _last_request_time = time.time()
    
    search_url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(query)
    
    # Improved headers to avoid detection
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        res.raise_for_status()
        
        # Multiple regex patterns for better matching
        patterns = [
            r'"videoId":"([a-zA-Z0-9_-]{11})"',  # JSON format
            r'/watch\?v=([a-zA-Z0-9_-]{11})',    # URL format
            r'watch\?v=([a-zA-Z0-9_-]{11})',     # Simple format
            r'"url":"/watch\?v=([a-zA-Z0-9_-]{11})"'  # Embedded URL
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, res.text)
            if matches:
                return "https://www.youtube.com/watch?v=" + matches[0]
        
        return "No video found."
        
    except requests.RequestException as e:
        return f"Search error: {str(e)}"
    except Exception as e:
        return "No video found."

@tool
def youtube_search_tool(query: str) -> str:
    """
    Search YouTube and return the first video link.
    """
    return search_youtube_scrape(query)