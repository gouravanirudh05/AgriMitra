import requests
import re

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
    res = requests.get(search_url, headers=headers)

    # Find the first /watch?v= video link
    matches = re.findall(r"/watch\?v=[\w-]{11}", res.text)
    if matches:
        return "https://www.youtube.com" + matches[0]

    return "No video found."
