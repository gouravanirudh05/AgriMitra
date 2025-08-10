# subagents/market_subagent.py
import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from tools.agri_market import get_market_price, list_market_commodities, list_market_states

logger = logging.getLogger(__name__)

class MarketSubAgent:
    """Subagent for handling agricultural market price queries using LangChain structured agent."""

    def __init__(self, config: Optional[Dict] = None, memory=None, callbacks=None):
        self.config = config or {}
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            convert_system_message_to_human=True
        )

        # If these are already Tool objects, just pass them in
        self.tools = [
            get_market_price,
            list_market_commodities,
            list_market_states
        ]

        agent_kwargs = {
            "prefix": "You are an agricultural market expert. Use the provided tools to answer user queries accurately.",
            "suffix": "Provide clear and helpful answers for farmers and traders."
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
        """Pass the query to the LangChain agent and let it pick and call the tools."""
        try:
            logger.info(f"Market subagent processing: {query[:200]}")
            result = self.agent_executor.run(query)
            return {
                "success": True,
                "tool_used": None,  # The agent may use multiple tools internally
                "raw_result": result,
                "summary": result,
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
