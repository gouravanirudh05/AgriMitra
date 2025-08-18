# subagents/fertilizer_subagent.py
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

# Import fertilizer-related tools
from tools.fertilizer import (
    get_recommendation,
    # get_fertilizer_recommendation,
    # list_supported_crops,
    # list_supported_districts
)

logger = logging.getLogger(__name__)

class FertilizerSubAgent:
    """Subagent for handling fertilizer recommendation queries using LangGraph ReAct agent."""

    def __init__(self, config: Optional[Dict] = None, memory=None, callbacks=None):
        self.config = config or {}

        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            # convert_system_message_to_human=True
        )

        # List of tools for the agent to use
        self.tools = [
            get_recommendation,
            # get_fertilizer_recommendation,
            # list_supported_crops,
            # list_supported_districts
        ]

        # Merge old prefix + suffix into a single SystemMessage
        system_prompt = SystemMessage(content=(
            "You are an expert in agricultural fertilizer recommendations. "
            "Use the provided tools to answer queries about fertilizer needs "
            "based on soil nutrients, location, and crop type. "
            "Give farmers clear, actionable fertilizer advice, "
            "including recommended NPK values and organic carbon needs."
            "Try using the recommendation tool to get a recommendation for fertilizer."
        ))

        # Create the ReAct agent
        self.agent_executor = create_react_agent(
            name="fertilizer-agent",
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt
        )

        # Keep for possible future use
        self.memory = memory
        self.callbacks = callbacks

    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Send the query to the LangGraph ReAct agent and return the response."""
        try:
            logger.info(f"Fertilizer subagent processing: {query[:200]}")

            # Build message list
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": query})

            # Run the agent
            result = self.agent_executor.invoke({"messages": messages})

            # Extract the final output
            answer = result["messages"][-1].content

            return {
                "success": True,
                "tool_used": None,  # Track via callbacks if needed
                "raw_result": result,
                "summary": answer,
                "error": None
            }
        except Exception as e:
            logger.exception("Fertilizer subagent error")
            return {
                "success": False,
                "tool_used": None,
                "raw_result": None,
                "summary": None,
                "error": str(e)
            }

    def get_capabilities(self) -> Dict[str, Any]:
        """Describe the agent's capabilities."""
        return {
            "name": "Fertilizer Recommendation Subagent",
            "description": (
                "Provides fertilizer recommendations based on soil NPK and organic carbon values, "
                "location, and crop type."
            ),
            "tools": [tool.name for tool in self.tools],
        }
