# subagents/youtube_subagent.py (Improved)
import os
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.youtube_search_tool import youtube_search_tool

logger = logging.getLogger(__name__)

class YouTubeSubAgent:
    """Subagent for handling YouTube video searches"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            convert_system_message_to_human=True
        )
        self.tool = youtube_search_tool
        self.name = "YouTube Subagent"
        self.description = "Handles YouTube video searches for educational and agricultural content"
        
        # Cache to avoid repeated searches for same query
        self._search_cache = {}
    
    def should_handle_query(self, query: str) -> bool:
        """Check if this query should be handled by YouTube subagent"""
        query_lower = query.lower()
        
        # Explicit video requests
        explicit_video_keywords = [
            'show me video', 'find video', 'youtube video', 'watch video',
            'video tutorial', 'learning video', 'educational video', 
            'demonstration video', 'tutorial video', 'video about',
            'video on', 'videos about'
        ]
        
        return any(keyword in query_lower for keyword in explicit_video_keywords)
    
    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process YouTube search queries"""
        try:
            logger.info(f"YouTube subagent processing: {query[:100]}...")
            
            # Check if this query should really be handled by YouTube subagent
            if not self.should_handle_query(query):
                return {
                    'success': False,
                    'error': 'Query does not explicitly request video content',
                    'tool_used': 'youtube_search',
                    'raw_result': None,
                    'summary': 'This query should be handled by knowledge subagent instead',
                    'should_redirect': 'knowledge'
                }
            
            # Extract search terms and optimize for agricultural content
            search_query = self._optimize_search_query(query)
            
            # Check cache first
            if search_query in self._search_cache:
                logger.info(f"Using cached result for: {search_query}")
                result = self._search_cache[search_query]
            else:
                # Search YouTube
                result = self.tool.func(search_query)
                # Cache the result
                self._search_cache[search_query] = result
            
            # Validate result quality
            if self._is_irrelevant_result(result, search_query):
                # Try a more specific search
                refined_query = self._refine_search_query(search_query)
                if refined_query != search_query:
                    logger.info(f"Trying refined search: {refined_query}")
                    result = self.tool.func(refined_query)
                    self._search_cache[refined_query] = result
            
            # Create enhanced response
            summary = self._create_enhanced_response(result, search_query, query)
            
            return {
                'success': True,
                'tool_used': 'youtube_search',
                'raw_result': result,
                'summary': summary,
                'search_query_used': search_query,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"YouTube subagent error: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool_used': 'youtube_search',
                'raw_result': None,
                'summary': f"YouTube search encountered an error: {e}"
            }
    
    def _is_irrelevant_result(self, result: str, search_query: str) -> bool:
        """Check if the search result is irrelevant to the query"""
        if result == "No video found.":
            return False  # This is a valid response
        
        # Check for common irrelevant results
        irrelevant_patterns = [
            'lofi', 'music', 'beats', 'chill', 'relaxing',
            'game', 'gaming', 'entertainment', 'comedy'
        ]
        
        result_lower = result.lower()
        search_lower = search_query.lower()
        
        # If result contains irrelevant patterns but search query doesn't
        if any(pattern in result_lower for pattern in irrelevant_patterns) and \
           not any(pattern in search_lower for pattern in irrelevant_patterns):
            return True
        
        return False
    
    def _refine_search_query(self, query: str) -> str:
        """Refine search query for better results"""
        # Add more specific terms to narrow down results
        refined_query = f"{query} farming agriculture tutorial guide"
        
        # Remove common words that might lead to irrelevant results
        words_to_remove = ['music', 'beats', 'lofi', 'chill']
        for word in words_to_remove:
            refined_query = refined_query.replace(word, '').strip()
        
        return refined_query
    
    def _optimize_search_query(self, query: str) -> str:
        """Optimize search query for better agricultural/educational content results"""
        # Remove YouTube-specific keywords
        youtube_keywords = ['youtube', 'video', 'watch', 'show me', 'find', 'search']
        words = query.lower().split()
        
        # Filter out YouTube keywords
        filtered_words = [word for word in words if word not in youtube_keywords]
        
        if not filtered_words:
            return query
        
        optimized_query = ' '.join(filtered_words)
        
        # Add context keywords for better agricultural results
        agricultural_context = [
            'farming', 'agriculture', 'crop', 'soil', 'irrigation', 
            'pest', 'fertilizer', 'organic', 'harvest'
        ]
        
        # If query seems agricultural but lacks context, add relevant keywords
        if any(keyword in optimized_query.lower() for keyword in agricultural_context):
            # Query already has agricultural context
            return f"{optimized_query} tutorial guide"
        else:
            # Add agricultural context for better results
            return f"{optimized_query} agriculture farming tutorial"
    
    def _create_enhanced_response(self, result: str, search_query: str, original_query: str) -> str:
        """Create enhanced response with context and recommendations"""
        try:
            if result == "No video found." or "error" in result.lower():
                prompt = f"""
                The user asked: "{original_query}"
                We searched for: "{search_query}"
                But no video was found.
                
                Please provide a helpful response that:
                1. Acknowledges that no specific video was found for their request
                2. Suggests alternative search terms they could try
                3. Recommends general agricultural YouTube channels or topics
                4. Offers to help refine their search query
                
                Keep it encouraging and helpful.
                """
                
                response = self.llm.invoke(prompt)
                return f"📹 **YouTube Search Results:**\n\n{response.content}"
            
            else:
                prompt = f"""
                The user asked: "{original_query}"
                We searched for: "{search_query}"
                Found video: {result}
                
                Please provide a helpful response that:
                1. Confirms we found a relevant video
                2. Explains how this video relates to their query
                3. Suggests what they might learn from watching it
                4. Offers to search for related topics if needed
                5. Include the video link prominently
                
                Make it engaging and educational. Focus on the value this video provides.
                """
                
                response = self.llm.invoke(prompt)
                return f"📹 **YouTube Search Results:**\n\n{response.content}\n\n🔗 **Video Link:** {result}"
            
        except Exception as e:
            logger.error(f"Error creating enhanced response: {e}")
            if result != "No video found.":
                return f"📹 **YouTube Video Found:** {result}\n\nThis video should help with your query about: {original_query}"
            else:
                return f"📹 **YouTube Search:** No video found for '{search_query}'. Try refining your search terms."
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return subagent capabilities"""
        return {
            'name': self.name,
            'description': self.description,
            'tools': ['youtube_search'],
            'supported_queries': [
                'Show me video about [topic]',
                'Find YouTube videos on farming techniques',
                'Video tutorial for [agricultural practice]',
                'Educational videos about agriculture',
                'YouTube videos on organic farming',
                'Demonstration videos for [farming technique]'
            ],
            'explicit_keywords_required': [
                'video', 'youtube', 'watch', 'show me video', 'find video',
                'video tutorial', 'demonstration video'
            ]
        }