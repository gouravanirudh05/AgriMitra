# subagents/market_subagent.py
import os
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.agri_market import get_market_price, list_market_commodities, list_market_states

logger = logging.getLogger(__name__)

class MarketSubAgent:
    """Subagent for handling agricultural market price queries"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            convert_system_message_to_human=True
        )
        self.tools = {
            'market_price': get_market_price,
            'list_commodities': list_market_commodities,
            'list_states': list_market_states
        }
        self.name = "Market Price Subagent"
        self.description = "Handles agricultural commodity prices, market data, and trading information from AgMarkNet"
    
    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process market price queries"""
        try:
            logger.info(f"Market subagent processing: {query[:100]}...")
            
            # Determine which tool to use
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in ['list commodities', 'available commodities', 'show commodities']):
                result = self.tools['list_commodities'].func()
                tool_used = 'list_commodities'
                summary = self._summarize_commodities_result(result, query)
                
            elif any(keyword in query_lower for keyword in ['list states', 'available states', 'show states']):
                result = self.tools['list_states'].func()
                tool_used = 'list_states'
                summary = self._summarize_states_result(result, query)
                
            else:
                # Price query
                result = self.tools['market_price'].func(query)
                tool_used = 'market_price'
                summary = self._summarize_price_result(result, query)
            
            return {
                'success': True,
                'tool_used': tool_used,
                'raw_result': result,
                'summary': summary,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Market subagent error: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool_used': None,
                'raw_result': None,
                'summary': f"Market price subagent encountered an error: {e}"
            }
    
    def _summarize_price_result(self, result: str, original_query: str) -> str:
        """Summarize market price results using LLM"""
        try:
            if "❌" in result or "error" in result.lower():
                return f"💰 **Market Price Query:** {result}"
            
            prompt = f"""
            The user asked: "{original_query}"
            
            Market data retrieved:
            {result}
            
            Please provide a comprehensive analysis that includes:
            1. Key price insights (highest, lowest, average prices if visible)
            2. Market trends (if multiple dates are shown)
            3. Regional variations (if multiple markets are shown)
            4. Price range and volatility observations
            5. Practical insights for farmers/traders
            6. Any notable patterns in the data
            
            Format with clear headings and bullet points. Make it actionable for farmers and traders.
            If the data shows a table, highlight the most important price points.
            """
            
            response = self.llm.invoke(prompt)
            return f"💰 **Market Price Analysis:**\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Error summarizing price result: {e}")
            return f"💰 **Market Prices:** {result[:300]}..."
    
    def _summarize_commodities_result(self, result: str, original_query: str) -> str:
        """Summarize commodities list"""
        try:
            prompt = f"""
            The user asked: "{original_query}"
            
            Available commodities:
            {result}
            
            Provide a helpful response that:
            1. Acknowledges their request for commodity information
            2. Highlights the variety of commodities available
            3. Groups them by category (grains, vegetables, spices, etc.) if possible
            4. Guides them on how to get prices for specific commodities
            5. Mentions any popular or commonly traded items
            
            Keep it organized and user-friendly.
            """
            
            response = self.llm.invoke(prompt)
            return f"🌾 **Available Market Commodities:**\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Error summarizing commodities result: {e}")
            return f"🌾 **Available Commodities:** {result[:200]}..."
    
    def _summarize_states_result(self, result: str, original_query: str) -> str:
        """Summarize states list"""
        try:
            prompt = f"""
            The user asked: "{original_query}"
            
            Available states:
            {result}
            
            Provide a helpful response that:
            1. Acknowledges their request for state information
            2. Mentions the coverage across different regions of India
            3. Guides them on how to get market prices for specific states
            4. Suggests they can combine state with commodity for price queries
            
            Keep it helpful and concise.
            """
            
            response = self.llm.invoke(prompt)
            return f"🗺️ **Available Market States:**\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Error summarizing states result: {e}")
            return f"🗺️ **Available States:** {result[:200]}..."
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return subagent capabilities"""
        return {
            'name': self.name,
            'description': self.description,
            'tools': list(self.tools.keys()),
            'supported_queries': [
                '[Commodity] prices in [State]',
                'Market data for [commodity] in [state]',
                'Price trends for [commodity]',
                'List available commodities',
                'List available states',
                'Current market rates',
                '[Commodity] market analysis'
            ]
        }