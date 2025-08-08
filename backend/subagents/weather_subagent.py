# subagents/weather_subagent.py
import os
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.weather_tool import weather_tool, weather_districts_tool

logger = logging.getLogger(__name__)

class WeatherSubAgent:
    """Subagent for handling weather-related queries and tools"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            convert_system_message_to_human=True
        )
        self.tools = {
            'weather': weather_tool,
            'weather_districts': weather_districts_tool
        }
        self.name = "Weather Subagent"
        self.description = "Handles weather forecasts and meteorological information for Indian districts"
    
    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process weather-related queries"""
        try:
            logger.info(f"Weather subagent processing: {query[:100]}...")
            
            # Determine which tool to use based on query
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in ['list', 'available', 'districts', 'show districts']):
                # Use districts tool
                result = self.tools['weather_districts'].func()
                summary = self._summarize_districts_result(result, query)
            else:
                # Extract district name for weather query
                district = self._extract_district(query)
                if not district:
                    return {
                        'success': False,
                        'error': 'Please specify a district name for weather information',
                        'tool_used': 'weather',
                        'raw_result': None,
                        'summary': 'No district specified in the query'
                    }
                
                # Get weather data
                result = self.tools['weather'].func(district)
                summary = self._summarize_weather_result(result, district, query)
            
            return {
                'success': True,
                'tool_used': 'weather' if 'list' not in query_lower else 'weather_districts',
                'raw_result': result,
                'summary': summary,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Weather subagent error: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool_used': None,
                'raw_result': None,
                'summary': f"Weather subagent encountered an error: {e}"
            }
    
    def _extract_district(self, query: str) -> Optional[str]:
        """Extract district name from query"""
        # Remove weather-related keywords to isolate district name
        weather_keywords = [
            'weather', 'forecast', 'temperature', 'rainfall', 'humidity',
            'climate', 'conditions', 'report', 'update', 'info', 'information',
            'for', 'in', 'of', 'get', 'show', 'tell', 'me', 'about'
        ]
        
        words = query.lower().split()
        district_words = []
        
        for word in words:
            clean_word = word.strip('.,!?')
            if clean_word not in weather_keywords and len(clean_word) > 2:
                district_words.append(word.strip('.,!?'))
        
        if district_words:
            return ' '.join(district_words).title()
        
        return None
    
    def _summarize_weather_result(self, result: str, district: str, original_query: str) -> str:
        """Summarize weather information using LLM"""
        try:
            if "error" in result.lower() or "not found" in result.lower():
                return f"⚠️ Weather data not available for {district}. {result}"
            
            prompt = f"""
            Analyze this weather bulletin and provide a concise summary focusing on key information.
            
            District: {district}
            Original Query: {original_query}
            Weather Bulletin:
            {result}
            
            Please provide:
            1. Current weather conditions (if available)
            2. Temperature information (if available)
            3. Rainfall/precipitation details (if available)
            4. Any weather warnings or advisories
            5. Forecast for next few days (if available)
            
            Format as a clear, concise summary with bullet points. Focus on the most relevant information for the query.
            """
            
            response = self.llm.invoke(prompt)
            return f"🌤️ **Weather Summary for {district}:**\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Error summarizing weather result: {e}")
            return f"🌤️ **Weather for {district}:** Raw weather data retrieved successfully. {result[:200]}..."
    
    def _summarize_districts_result(self, result: str, original_query: str) -> str:
        """Summarize districts list"""
        try:
            prompt = f"""
            The user asked: "{original_query}"
            
            Here's the list of available districts:
            {result}
            
            Provide a helpful response that:
            1. Acknowledges their request
            2. Mentions the total number of districts available
            3. Shows a few example districts
            4. Guides them on how to get weather for a specific district
            
            Keep it concise and helpful.
            """
            
            response = self.llm.invoke(prompt)
            return f"🗺️ **Available Weather Districts:**\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Error summarizing districts result: {e}")
            return f"🗺️ **Available Districts:** {result[:200]}..."
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return subagent capabilities"""
        return {
            'name': self.name,
            'description': self.description,
            'tools': list(self.tools.keys()),
            'supported_queries': [
                'Weather forecast for [district]',
                'Temperature in [district]',
                'Rainfall in [district]',
                'List available districts',
                'Weather conditions in [district]'
            ]
        }