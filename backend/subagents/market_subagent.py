# subagents/market_subagent.py
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from tools.agri_market import get_market_price, list_market_commodities, list_market_states
from datetime import date
logger = logging.getLogger(__name__)

class MarketSubAgent:
    """Subagent for handling agricultural market price queries using LangGraph ReAct agent."""

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
            get_market_price,
            list_market_commodities,
            list_market_states
        ]
        self.today = date.today()
        # Combine old agent_kwargs prefix + suffix into a single system message
        system_prompt = SystemMessage(content=(
            "Today's date is " + self.today.strftime("%d-%m-%Y") + "."
            "You are an agricultural market expert. "
            "Use the provided tools to answer user queries accurately. "
            "Provide clear and helpful answers for farmers and traders."
            "If the query asks for current market prices, or just the price of a commodity, use the get_market_price tool with today's date as end date (and also start date)."
            "Assume the place given in the query is the current location/state."
        ))

        # Create the ReAct agent
        self.agent_executor = create_react_agent(
            name="market-agent",
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt
        )

        # Keep these if you plan to implement custom memory/callback logic
        self.memory = memory
        self.callbacks = callbacks

    def process_query(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Pass the query to the LangGraph ReAct agent and let it pick and call the tools."""
        try:
            logger.info(f"Market subagent processing: {query[:200]}")

            # Build message list for the agent
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": query})

            # Call the ReAct agent
            result = self.agent_executor.invoke({"messages": messages})

            # Extract the final output
            answer = result["messages"][-1].content

            return {
                "success": True,
                "tool_used": None,  # Can be tracked via callbacks if needed
                "raw_result": result,
                "summary": answer,
                "error": None
            }
        except Exception as e:
            logger.exception("Market subagent error")
            return {
                "success": False,
                "tool_used": None,
                "raw_result": None,
                "summary": None,
                "error": str(e)
            }

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Market Price Subagent",
            "description": "Handles agricultural commodity prices, market data, and trading information from AgMarkNet",
            "tools": [tool.name for tool in self.tools],
        }
