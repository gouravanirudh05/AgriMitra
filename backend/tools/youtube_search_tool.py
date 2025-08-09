import requests
import re
from langchain.tools import tool

def search_youtube_scrape(query: str) -> str:
    """
    Searches YouTube's own search page and returns the first video link.
    Does NOT use YouTube API.
    """
    search_url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(query)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }
    res = requests.get(search_url, headers=headers, timeout=10)

    if res.status_code != 200:
        return f"Error fetching results: {res.status_code}"

    # Look for video IDs inside JSON/script content
    matches = re.findall(r'\/watch\?v=([a-zA-Z0-9_-]{11})', res.text)
    if matches:
        # Deduplicate while preserving order
        seen = set()
        unique_ids = [x for x in matches if not (x in seen or seen.add(x))]
        return "https://www.youtube.com/watch?v=" + unique_ids[0]

    return "No video found."

@tool
def youtube_search_tool(query: str) -> str:
    """
    Search YouTube and return the first video link.
    """
    return search_youtube_scrape(query)
