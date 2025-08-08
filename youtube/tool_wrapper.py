from langchain.tools import tool
from search_youtube import search_youtube_scrape

@tool
def youtube_search_tool(query: str) -> str:
    """
    Search YouTube for a video matching the given query and return the first link.
    Does not use YouTube API — scrapes Google search results.
    """
    return search_youtube_scrape(query)
