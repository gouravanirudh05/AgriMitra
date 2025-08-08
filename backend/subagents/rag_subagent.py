# subagents/rag_subagent.py
import os
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.rag_tool import rag_tool

logger = logging.getLogger(__name__)

class RAGSubAgent:
    """Subagent for handling knowledge base queries and document retrieval"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            convert_system_message_to_human=True
        )
        self.tool = rag_tool
        self.name = "Knowledge Subagent"
        self.description = "Handles knowledge base searches, agricultural information, government schemes, and document retrieval"
    
    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process knowledge base queries"""
        try:
            logger.info(f"RAG subagent processing: {query[:100]}...")
            
            # Use the RAG tool to search knowledge base
            result = self.tool.func(query)
            
            # Enhance the result with better summarization
            summary = self._enhance_knowledge_result(result, query)
            
            return {
                'success': True,
                'tool_used': 'knowledge_search',
                'raw_result': result,
                'summary': summary,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"RAG subagent error: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool_used': 'knowledge_search',
                'raw_result': None,
                'summary': f"Knowledge search encountered an error: {e}"
            }
    
    def _enhance_knowledge_result(self, result: str, original_query: str) -> str:
        """Enhance knowledge search results with better formatting and context"""
        try:
            if "error" in result.lower() or "not found" in result.lower():
                return f"🔍 **Knowledge Search:** {result}"
            
            prompt = f"""
            The user asked: "{original_query}"
            
            Knowledge base search returned:
            {result}
            
            Please enhance this response by:
            1. Structuring the information clearly with proper headings
            2. Highlighting key points and actionable information
            3. Adding context about how this relates to the user's question
            4. If this is about government schemes, include eligibility and application process
            5. If this is about farming practices, include practical implementation steps
            6. Preserve any source citations that were in the original result
            
            Format with markdown for better readability. Keep the enhanced response comprehensive but well-organized.
            """
            
            response = self.llm.invoke(prompt)
            return f"📚 **Knowledge Base Results:**\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Error enhancing knowledge result: {e}")
            return f"📚 **Knowledge Base:** {result}"
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return subagent capabilities"""
        return {
            'name': self.name,
            'description': self.description,
            'tools': ['knowledge_search'],
            'supported_queries': [
                'PM Kisan Yojana information',
                'Organic farming practices',
                'Crop rotation techniques',
                'Fertilizer recommendations',
                'Pest management strategies',
                'Soil health management',
                'Irrigation techniques',
                'Government agricultural schemes',
                'Agricultural policies',
                'Farming best practices'
            ]
        }