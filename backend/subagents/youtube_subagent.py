# subagents/youtube_subagent.py (Fixed - More Flexible)
import os
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.youtube_search_tool import youtube_search_tool

logger = logging.getLogger(__name__)

class YouTubeSubAgent:
    """Subagent for handling YouTube video searches - Now with flexible query handling"""
    
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
        """
        More flexible check - if the orchestrator routes here, we should handle it.
        This method is now primarily for backward compatibility.
        """
        query_lower = query.lower()
        
        # Always handle if routed by orchestrator (contains video-related terms broadly)
        video_indicators = [
            'video', 'youtube', 'tutorial', 'demonstration', 'show', 'watch',
            'tips', 'guide', 'learn', 'how to', 'educational', 'training',
            'clip', 'channel', 'playlist'
        ]
        
        # More lenient - if any video indicator is present OR if query asks for learning content
        has_video_indicators = any(indicator in query_lower for indicator in video_indicators)
        
        # Also handle queries that imply wanting to learn something (likely want videos)
        learning_indicators = [
            'tips', 'techniques', 'methods', 'ways to', 'how to', 'guide',
            'tutorial', 'learn', 'training', 'steps', 'process'
        ]
        has_learning_indicators = any(indicator in query_lower for indicator in learning_indicators)
        
        return has_video_indicators or has_learning_indicators
    
    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process YouTube search queries with more flexible handling"""
        try:
            logger.info(f"YouTube subagent processing: {query[:100]}...")
            
            # Since we're routed here by Gemini, trust the routing decision
            # Only reject if it's completely inappropriate (e.g., weather data request)
            if self._is_completely_inappropriate(query):
                return {
                    'success': False,
                    'error': 'Query is not suitable for video search',
                    'tool_used': 'youtube_search',
                    'raw_result': None,
                    'summary': 'This query should be handled by a different subagent',
                    'should_redirect': 'knowledge'
                }
            
            # Extract search terms and optimize for agricultural content
            search_query = self._optimize_search_query(query)
            
            logger.info(f"Optimized search query: {search_query}")
            
            # Check cache first
            if search_query in self._search_cache:
                logger.info(f"Using cached result for: {search_query}")
                result = self._search_cache[search_query]
            else:
                # Search YouTube
                logger.info(f"Searching YouTube for: {search_query}")
                result = self.tool.func(search_query)
                # Cache the result
                self._search_cache[search_query] = result
            
            logger.info(f"YouTube search result: {result}")
            
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
    
    def _is_completely_inappropriate(self, query: str) -> bool:
        """Check if query is completely inappropriate for video search"""
        query_lower = query.lower()
        
        # Only reject queries that are clearly not video-related
        inappropriate_patterns = [
            'current weather', 'temperature today', 'weather forecast',
            'market price', 'commodity price', 'stock price',
            'what is the price of', 'how much does', 'cost of'
        ]
        
        return any(pattern in query_lower for pattern in inappropriate_patterns)
    
    def _is_irrelevant_result(self, result: str, search_query: str) -> bool:
        """Check if the search result is irrelevant to the query"""
        if result == "No video found." or "error" in result.lower():
            return False  # This is a valid response, not irrelevant
        
        # Check for common irrelevant results
        irrelevant_patterns = [
            'lofi', 'music beats', 'chill music', 'relaxing music',
            'gaming', 'entertainment', 'comedy show', 'memes'
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
        refined_query = f"{query} farming agriculture tutorial how to"
        
        # Remove common words that might lead to irrelevant results
        words_to_remove = ['music', 'beats', 'lofi', 'chill', 'entertainment']
        for word in words_to_remove:
            refined_query = refined_query.replace(word, '').strip()
        
        # Clean up extra spaces
        refined_query = ' '.join(refined_query.split())
        
        return refined_query
    
    def _optimize_search_query(self, query: str) -> str:
        """Optimize search query for better agricultural/educational content results"""
        # Remove YouTube-specific keywords that don't add value to search
        youtube_keywords_to_remove = ['youtube', 'video', 'watch', 'show me', 'find']
        words = query.lower().split()
        
        # Filter out non-helpful YouTube keywords
        filtered_words = [word for word in words if word not in youtube_keywords_to_remove]
        
        if not filtered_words:
            # If all words were filtered, use original query
            optimized_query = query
        else:
            optimized_query = ' '.join(filtered_words)
        
        # Clean up common phrases
        optimized_query = optimized_query.replace('give me', '').replace('show me', '').strip()
        
        # Ensure we have meaningful content
        if len(optimized_query.strip()) < 3:
            optimized_query = query  # Fallback to original
        
        # Add educational context keywords for better results
        educational_boosters = []
        
        # Check if query is about farming/agriculture
        if any(term in optimized_query.lower() for term in ['farm', 'crop', 'soil', 'plant', 'grow']):
            educational_boosters.append('agriculture')
        
        # Add tutorial context if not present
        if 'tutorial' not in optimized_query.lower() and 'how to' not in optimized_query.lower():
            educational_boosters.append('tutorial')
        
        # Combine original query with boosters
        final_query = optimized_query
        if educational_boosters:
            final_query = f"{optimized_query} {' '.join(educational_boosters)}"
        
        # Clean up and return
        return ' '.join(final_query.split())  # Remove extra spaces
    
    def _create_enhanced_response(self, result: str, search_query: str, original_query: str) -> str:
        """Create enhanced response with context and recommendations"""
        try:
            if result == "No video found." or "error" in result.lower():
                prompt = f"""
                The user asked: "{original_query}"
                We searched YouTube for: "{search_query}"
                But no video was found.
                
                Please provide a helpful response that:
                1. Acknowledges that no specific video was found for their request
                2. Suggests alternative search terms they could try on YouTube
                3. Recommends popular agricultural YouTube channels they might find useful
                4. Offers to help search for related topics
                
                Keep it encouraging and helpful. Format with emojis and clear sections.
                """
                
                response = self.llm.invoke(prompt)
                return f"📹 **YouTube Search Results**\n\n{response.content}"
            
            else:
                prompt = f"""
                The user asked: "{original_query}"
                We searched for: "{search_query}"
                Found this video: {result}
                
                Please provide a helpful response that:
                1. Confirms we found a relevant video
                2. Explains how this video relates to their original query
                3. Suggests what they might learn from watching it
                4. Offers to search for related or more specific topics if needed
                5. Make it engaging and educational
                
                Keep it concise but informative. Use emojis appropriately.
                """
                
                response = self.llm.invoke(prompt)
                return f"📹 **YouTube Video Found**\n\n{response.content}\n\n🔗 **Direct Link:** {result}"
            
        except Exception as e:
            logger.error(f"Error creating enhanced response: {e}")
            # Fallback response
            if result != "No video found." and "error" not in result.lower():
                return f"📹 **YouTube Video Found**\n\n🎯 Found a relevant video for your query: \"{original_query}\"\n\n🔗 **Watch here:** {result}\n\n💡 This video should help you with farming tips and techniques!"
            else:
                return f"📹 **YouTube Search Complete**\n\n🔍 Searched for: \"{search_query}\"\n\n⚠️ No videos found with those exact terms. Try searching YouTube directly with broader terms like:\n• \"farming tips for beginners\"\n• \"agriculture techniques\"\n• \"organic farming methods\"\n\nWould you like me to search for something more specific?"
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return subagent capabilities"""
        return {
            'name': self.name,
            'description': self.description,
            'tools': ['youtube_search'],
            'supported_queries': [
                'farming tips videos',
                'Show me video about [topic]',
                'Find YouTube videos on farming techniques', 
                'Video tutorial for [agricultural practice]',
                'Educational videos about agriculture',
                'YouTube videos on organic farming',
                'Demonstration videos for [farming technique]',
                'How to videos for farming',
                'Agricultural training videos'
            ],
            'flexibility': 'high',
            'routing_trust': 'trusts_orchestrator_routing'
        }