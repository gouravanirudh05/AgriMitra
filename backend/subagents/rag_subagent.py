# subagents/rag_subagent.py
import os
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.rag_tool import rag_tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)

class RAGSubAgent:
    """Enhanced subagent for handling knowledge base queries and document retrieval with LLM fallback"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            safety_settings={
                7: 0,  # HARM_CATEGORY_HARASSMENT: BLOCK_NONE
                8: 0,  # HARM_CATEGORY_HATE_SPEECH: BLOCK_NONE
                9: 0,  # HARM_CATEGORY_SEXUALLY_EXPLICIT: BLOCK_NONE
                10: 0, # HARM_CATEGORY_DANGEROUS_CONTENT: BLOCK_NONE
            }
        )
        self.tools = [rag_tool]
        self.name = "Knowledge Subagent"
        self.description = "Handles knowledge base searches, agricultural information, government schemes, and document retrieval with intelligent fallback responses"

        self.system_prompt = SystemMessage(content=(
            "You are an agricultural knowledge assistant. "
            "Use the knowledge base search tool to retrieve accurate information "
            "about crops, farming practices, government schemes, and rural development. "
            "If the retrieved information is insufficient, provide a clear, concise fallback response. "
            "Always keep answers farmer-friendly, structured, and under 200 words unless detailed explanation is requested."
        ))
        
        self.agent_executor = create_react_agent(
            name="knowledge-agent",
            model=self.llm,
            tools=self.tools,
            prompt=self.system_prompt
        )
        
    
    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process knowledge base queries with enhanced fallback capabilities"""
        try:
            logger.info(f"RAG subagent processing: {query[:100]}...")
            
            # First, try the RAG tool to search knowledge base
            rag_result = self.tool.func(query)
            logger.info(f"RAG tool result length: {len(rag_result)}")
            
            # Check if the result indicates no relevant information was found
            needs_fallback = self._needs_llm_fallback(rag_result, query)
            
            if needs_fallback:
                logger.info("RAG result insufficient, using LLM fallback")
                # Use LLM to provide a comprehensive answer
                enhanced_result = self._provide_llm_fallback_response(query, rag_result)
                summary = self._format_hybrid_response(enhanced_result, rag_result, query)
                
                return {
                    'success': True,
                    'tool_used': 'knowledge_search_with_llm_fallback',
                    'raw_result': rag_result,
                    'enhanced_result': enhanced_result,
                    'summary': summary,
                    'fallback_used': True,
                    'error': None
                }
            else:
                # RAG result is good, enhance it
                summary = self._enhance_knowledge_result(rag_result, query)
                
                return {
                    'success': True,
                    'tool_used': 'knowledge_search',
                    'raw_result': rag_result,
                    'summary': summary,
                    'fallback_used': False,
                    'error': None
                }
            
        except Exception as e:
            logger.error(f"RAG subagent error: {e}")
            
            # Even if RAG tool fails, try to provide an LLM-based answer
            try:
                fallback_response = self._provide_llm_fallback_response(query, f"Error occurred: {e}")
                return {
                    'success': True,  # Still successful since we provided an answer
                    'error': f"RAG tool error: {e}",
                    'tool_used': 'llm_fallback_only',
                    'raw_result': None,
                    'summary': fallback_response,
                    'fallback_used': True
                }
            except Exception as fallback_error:
                return {
                    'success': False,
                    'error': f"Both RAG and LLM failed: RAG({e}), LLM({fallback_error})",
                    'tool_used': 'knowledge_search',
                    'raw_result': None,
                    'summary': f"I apologize, but I encountered technical difficulties searching for information about '{query}'. Please try rephrasing your question or ask about a different topic."
                }
    
    def _needs_llm_fallback(self, rag_result: str, query: str) -> bool:
        """Determine if the RAG result needs LLM fallback enhancement"""
        if not rag_result or len(rag_result.strip()) < 50:
            return True
        
        # Check for common indicators that no relevant info was found
        insufficient_indicators = [
            "error",
            "not found",
            "no relevant information",
            "couldn't find",
            "unable to find",
            "no information available",
            "not properly initialized",
            "please check configuration",
            "system not available"
        ]
        
        rag_lower = rag_result.lower()
        
        for indicator in insufficient_indicators:
            if indicator in rag_lower:
                return True
        
        # Check if response is too generic or doesn't seem to address the specific query
        query_keywords = set(query.lower().split())
        result_keywords = set(rag_result.lower().split())
        
        # If very few query keywords appear in result, it might not be relevant
        keyword_overlap = len(query_keywords.intersection(result_keywords))
        if len(query_keywords) > 2 and keyword_overlap < 2:
            return True
        
        return False
    
    def _provide_llm_fallback_response(self, query: str, rag_result: str) -> str:
        """Use LLM to provide comprehensive answer when RAG is insufficient"""
        try:
            prompt = f"""You are an expert agricultural advisor with comprehensive knowledge about farming practices, crop management, government schemes, agricultural technologies, and rural development.Give consicse answers
IMPORTANT: Keep responses under 200 words and focus on key points only. 
Use bullet points for clarity when listing multiple items.
Avoid lengthy explanations unless specifically requested.
User Query: "{query}"

Knowledge Base Search Result: "{rag_result}"

The knowledge base search either returned insufficient information or encountered an error. Please provide a comprehensive, helpful answer to the user's query using your agricultural expertise.

Guidelines:
1. Focus specifically on the user's question
2. Provide practical, actionable information
3. If it's about government schemes (like PM Kisan, Fasal Bima, etc.), include eligibility criteria and application processes
4. If it's about farming practices, include step-by-step guidance
5. If it's about crop management, include timing, techniques, and best practices
6. Include relevant precautions or considerations
7. Structure your response clearly with headings where appropriate
8. Keep the language simple and farmer-friendly
9. If you mention any schemes or programs, provide context about their purpose and benefits
10. DO NOT use emojis in your response

If the knowledge base provided some information, acknowledge it and expand upon it. If not, provide a complete answer based on your agricultural knowledge.

Provide a detailed, well-structured response:"""

            response = self.llm.invoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error in LLM fallback: {e}")
            return f"I understand you're asking about {query}. While I encountered a technical issue accessing specific information, I recommend consulting with local agricultural extension officers, checking the official websites of relevant government departments, or visiting the nearest Krishi Vigyan Kendra (KVK) for detailed guidance on this topic."
    
    def _format_hybrid_response(self, llm_response: str, rag_result: str, query: str) -> str:
        """Format response when using both RAG and LLM"""
        response = f"**Knowledge Base Response:**\n\n{llm_response}"
        
        # Only add RAG result info if it contains something useful
        if rag_result and not any(indicator in rag_result.lower() for indicator in ["error", "not found", "not properly initialized"]):
            response += f"\n\n**Additional Context from Documents:** {rag_result}"
        
        return response
    
    def _enhance_knowledge_result(self, result: str, original_query: str) -> str:
        """Enhance knowledge search results with better formatting and context"""
        try:
            if self._needs_llm_fallback(result, original_query):
                # If result is insufficient, use LLM fallback
                return self._provide_llm_fallback_response(original_query, result)
            
            prompt = f"""The user asked: "{original_query}"

Knowledge base search returned:
{result}

Please enhance this response by:
1. Structuring the information clearly with proper headings
2. Highlighting key points and actionable information  
3. Adding context about how this relates to the user's question
4. If this is about government schemes, include eligibility and application process
5. If this is about farming practices, include practical implementation steps
6. Preserve any source citations that were in the original result
7. Make it more comprehensive and user-friendly
8. DO NOT include emojis in the answer

Format with markdown for better readability. Keep the enhanced response comprehensive but well-organized."""
            
            response = self.llm.invoke(prompt)
            return f"**Knowledge Base Results:**\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Error enhancing knowledge result: {e}")
            # If enhancement fails, return original result
            return f"**Knowledge Base:** {result}"
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return subagent capabilities"""
        return {
            'name': self.name,
            'description': self.description,
            'tools': ['knowledge_search', 'llm_fallback'],
            'features': [
                'Vector database search',
                'Intelligent LLM fallback',
                'Hybrid response generation',
                'Agricultural expertise',
                'Government scheme information',
                'Farming practice guidance'
            ],
            'supported_queries': [
                'PM Kisan Yojana information',
                'Pradhan Mantri Fasal Bima Yojana',
                'Soil health card scheme',
                'Organic farming practices',
                'Crop rotation techniques',
                'Fertilizer recommendations',
                'Pest management strategies',
                'Soil health management',
                'Irrigation techniques',
                'Government agricultural schemes',
                'Agricultural policies',
                'Farming best practices',
                'Seed varieties and selection',
                'Post-harvest management',
                'Agricultural marketing',
                'Farm mechanization',
                'Sustainable agriculture',
                'Climate-smart agriculture'
            ]
        }