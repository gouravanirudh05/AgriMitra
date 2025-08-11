# subagents/weather_subagent.py
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from tools.weather_tool import weather_tool, weather_districts_tool

logger = logging.getLogger(__name__)

class WeatherSubAgent:
    """Subagent for handling weather-related queries via LangChain structured agent."""

    def __init__(self, config: Optional[Dict] = None, memory=None, callbacks=None):
        self.config = config or {}
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0.1,
            convert_system_message_to_human=True
        )

        # If these are already Tool objects, just pass them directly
        self.tools = [
            weather_tool,
            weather_districts_tool
        ]

        agent_kwargs = {
            "prefix": (
                "You are a weather expert for Indian districts. "
                "Use the provided tools to answer user queries. "
                "If the query asks for current or forecast weather in a district, "
                "use the weather tool with the correct district parameter. "
                "If the query asks for a list of districts, use the weather_districts tool."
            ),
            "suffix": "Provide a clear, concise, and helpful answer."
        }

        self.agent_executor = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=self.config.get("verbose", False),
            memory=memory,
            agent_kwargs=agent_kwargs,
            callbacks=callbacks,
            max_iterations=self.config.get("max_iterations", 5),
            max_execution_time=self.config.get("max_execution_time", None),
            handle_parsing_errors=True,
            return_intermediate_steps=False
        )

    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Pass the query to the LangChain agent and let it decide which tool to use."""
        try:
            logger.info(f"Weather subagent processing: {query[:200]}")
            result = self.agent_executor.run(query)
            return {
                "success": True,
                "tool_used": None,  # Agent may use multiple tools internally
                "raw_result": result,
                "summary": result,
                "error": None
            }
        except Exception as e:
            logger.exception("Weather subagent error")
            return {
                "success": False,
                "tool_used": None,
                "raw_result": None,
                "summary": None,
                "error": str(e)
            }

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Weather Subagent",
            "description": "Handles weather forecasts and meteorological information for Indian districts",
            "tools": [tool.name for tool in self.tools],
        }
