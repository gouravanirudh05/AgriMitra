# subagents/youtube_subagent.py

import os
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.youtube_search_tool import youtube_search_tool

logger = logging.getLogger(__name__)

class YouTubeAgentLink:
    """Subagent for handling YouTube video searches - Now with flexible query handling"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
        )
        self.tool = youtube_search_tool
        self.name = "YouTube Subagent"
        self.description = "Handles YouTube video searches for educational and agricultural content"
        
        # Cache to avoid repeated searches for same query
        self._search_cache = {}
    
    def _create_search_query(self, user_query: str, final_answer: str) -> str:
        """Generate a YouTube search query based on user query and final answer."""
        prompt = f"""
You are an assistant that creates short, relevant YouTube search queries for educational and practical purposes.

### Rules for deciding whether to create a YouTube search query:
1. If the user's query is **about current weather, rainfall, climate, or daily/weekly market prices**, DO NOT create a search query.  
   - Reason: This information changes rapidly, and videos will be outdated.  
   - In this case, respond only with: "NO_VIDEO"

2. If the user's query is about:
   - Government schemes (e.g., PM-Kisan, PMFBY, Fasal Bima Yojana)
   - How to apply for loans or subsidies
   - How to use agricultural machinery or farming techniques
   - Training, education, or tutorials
   - Step-by-step guides for registration or official processes
   - Awareness campaigns or policy explanations  
   THEN create a short YouTube search query that would help the user find an up-to-date, relevant, and trustworthy video.

3. Keep the search query:
   - Clear and specific
   - Maximum 10 words
   - Avoid quotation marks, punctuation, or unnecessary words
   - Prefer the official scheme/loan/method name + keywords like "how to apply", "registration process", "tutorial", etc.

4. Do not hallucinate new scheme names. Use only what is present in the query or final answer.

---

User query: {user_query}
Final answer: {final_answer}

Now, following the rules above, either:
- Output "NO_VIDEO" (exactly, without quotes), or
- Output a short YouTube search query.
"""
        result = self.llm.predict(prompt).strip()
        logger.debug(f"Generated YouTube search query: {result}")
        return result
    
    def get_youtube_video(self, user_query: str, final_answer: str) -> Optional[str]:
        """Return a YouTube video URL based on the query and final answer."""
        
        search_query = self._create_search_query(user_query, final_answer)
        if search_query=="NO_VIDEO":
            return ""
        video_url = self.tool(search_query)  # Assumes tool returns a URL
        
        if video_url:
            return video_url
        else:
            logger.warning(f"No video found for: {search_query}")
            return None


__youtube_agent_link__ = None

def get_YouTubeAgentLink() -> YouTubeAgentLink:
    """Get the global YouTubeAgentLink instance"""
    global __youtube_agent_link__
    if __youtube_agent_link__ is None:
        __youtube_agent_link__ = YouTubeAgentLink()
    return __youtube_agent_link__
