# subagents/weather_subagent.py
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from tools.weather_tool import weather_tool, weather_districts_tool

logger = logging.getLogger(__name__)

class WeatherSubAgent:
    """Subagent for handling weather-related queries via LangGraph ReAct agent."""

    def __init__(self, config: Optional[Dict] = None, memory=None, callbacks=None):
        self.config = config or {}

        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            # convert_system_message_to_human=True
        )

        # If these are already Tool objects, just pass them directly
        self.tools = [
            weather_tool,
            weather_districts_tool
        ]

        # Migrate agent_kwargs -> SystemMessage prompt
        system_prompt = SystemMessage(content=(
            "You are a weather expert for Indian districts. "
            "Use the provided tools to answer user queries. "
            "If the query asks for current or forecast weather in a district, "
            "use the weather tool with the correct district parameter. "
            "If the query asks for a list of districts, use the weather_districts tool. "
            "Provide a clear, concise, and helpful answer."
        ))

        # Create the ReAct agent
        self.agent_executor = create_react_agent(
            name="weather-agent",
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt
        )

        # Store optional extras if you need to handle memory/logging yourself
        self.memory = memory
        self.callbacks = callbacks

    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Pass the query to the LangGraph ReAct agent and let it decide which tool to use."""
        try:
            logger.info(f"Weather subagent processing: {query[:200]}")

            # Build message history — LangGraph expects messages, not raw strings
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": query})

            result = self.agent_executor.invoke({"messages": messages})

            # Final output is in the last message from the agent
            answer = result["messages"][-1].content

            return {
                "success": True,
                "tool_used": None,  # Could be tracked via callbacks if needed
                "raw_result": result,
                "summary": answer,
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
