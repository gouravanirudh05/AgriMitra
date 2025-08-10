# enhanced_orchestrator.py (LangGraph Supervisor Integration with Gemini Routing)
import os
import logging
from typing import Dict, Any, Optional, List, Annotated
import asyncio
from pathlib import Path
import dotenv
from datetime import date
import re
# LangGraph imports
from langgraph.graph import StateGraph, START, MessagesState, END
from langgraph.types import Command, Send
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import convert_to_messages, HumanMessage, AIMessage, ToolMessage

# Try to import create_react_agent, fall back to custom implementation
try:
    from langgraph.prebuilt import create_react_agent, InjectedState
    from langgraph_supervisor import create_supervisor
    LANGGRAPH_REACT_AVAILABLE = True
except ImportError:
    try:
        from langgraph.prebuilt import InjectedState
        LANGGRAPH_REACT_AVAILABLE = False
    except ImportError:
        LANGGRAPH_REACT_AVAILABLE = False
        InjectedState = None

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import StdOutCallbackHandler

# Import subagents (keep existing imports)
from subagents.weather_subagent import WeatherSubAgent
from subagents.rag_subagent import RAGSubAgent
from subagents.youtube_subagent import YouTubeSubAgent
from subagents.market_subagent import MarketSubAgent

# Import tools for backward compatibility
from tools.rag_tool import rag_tool
from tools.weather_tool import weather_tool, weather_districts_tool
from tools.youtube_search_tool import youtube_search_tool
from tools.agri_market import get_market_price, list_market_commodities, list_market_states

dotenv.load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for backward compatibility
agent_executor = None
agent_memory = None


class LangGraphSupervisorOrchestrator:
    """Enhanced orchestrator with LangGraph supervisor pattern and Gemini-based routing"""
    
    def __init__(self):
        self.subagents = {}
        self.llm = None
        self.routing_llm = None  # Separate LLM for routing decisions
        self.memory = None
        self.agent_executor = None  # For backward compatibility
        self.tools = []  # For backward compatibility
        self.supervisor_graph = None  # LangGraph supervisor
        self.is_initialized = False
        self.use_langgraph_supervisor = True
        
        # Configuration
        self.config = {
            'model': os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
            'temperature': float(os.getenv('AGENT_TEMPERATURE', '0')),
            'memory_window': int(os.getenv('MEMORY_WINDOW', '10')),
            'max_iterations': int(os.getenv('MAX_ITERATIONS', '15')),
            'max_execution_time': int(os.getenv('MAX_EXECUTION_TIME', '60')),
            'verbose': os.getenv('AGENT_VERBOSE', 'true').lower() == 'true',
            'use_langgraph_supervisor': os.getenv('USE_LANGGRAPH_SUPERVISOR', 'true').lower() == 'true'
        }
        
        self.use_langgraph_supervisor = self.config['use_langgraph_supervisor']
    
    def _validate_environment(self):
        """Validate required environment variables and dependencies"""
        required_env_vars = ['GOOGLE_API_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {missing_vars}")
        
        # Create necessary directories
        dirs_to_create = [
            Path(os.getenv('AGMARKNET_DATA_DIR', 'datasets')),
            Path(os.getenv('WEATHER_DOWNLOAD_DIR', 'downloads/weather')),
            Path('downloads'),
            Path('logs'),
            Path('subagents')
        ]
        
        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
    def _initialize_llm(self):
        """Initialize the Language Model"""
        try:
            # Main LLM for subagents
            self.llm = ChatGoogleGenerativeAI(
                model=self.config['model'],
                temperature=self.config['temperature'],
                convert_system_message_to_human=True,
                safety_settings={
                    7: 0,  # HARM_CATEGORY_HARASSMENT: BLOCK_NONE
                    8: 0,  # HARM_CATEGORY_HATE_SPEECH: BLOCK_NONE
                    9: 0,  # HARM_CATEGORY_SEXUALLY_EXPLICIT: BLOCK_NONE
                    10: 0, # HARM_CATEGORY_DANGEROUS_CONTENT: BLOCK_NONE
                }
            )
            
            # Routing LLM with higher temperature for better reasoning
            self.routing_llm = ChatGoogleGenerativeAI(
                model=self.config['model'],
                temperature=0.2,  # Slightly higher for routing decisions
                convert_system_message_to_human=True,
                safety_settings={
                    7: 0, 8: 0, 9: 0, 10: 0
                }
            )
            
            logger.info(f"LLMs initialized: {self.config['model']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")

    def _initialize_memory(self):
        """Initialize conversation memory"""
        try:
            self.memory = ConversationBufferWindowMemory(
                k=self.config['memory_window'],
                memory_key="chat_history",
                return_messages=True,
                output_key="output"
            )
            logger.info(f"Memory initialized with window size: {self.config['memory_window']}")
        except Exception as e:
            logger.error(f"Failed to initialize memory: {e}")
            self.memory = None
    
    def _initialize_subagents(self):
        """Initialize all subagents"""
        try:
            self.subagents = {
                'weather': WeatherSubAgent(),
                'knowledge': RAGSubAgent(),
                'youtube': YouTubeSubAgent(),
                'market': MarketSubAgent()
            }
            
            # Validate subagents
            valid_subagents = {}
            for name, subagent in self.subagents.items():
                try:
                    capabilities = subagent.get_capabilities()
                    valid_subagents[name] = subagent
                    logger.info(f"✅ Subagent validated: {capabilities['name']}")
                except Exception as e:
                    logger.error(f"❌ Subagent validation failed: {name} - {e}")
            
            self.subagents = valid_subagents
            logger.info(f"Initialized {len(self.subagents)} subagents: {list(self.subagents.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to initialize subagents: {e}")
            raise RuntimeError(f"Subagent initialization failed: {e}")
    
    async def _classify_query_with_gemini(self, query: str) -> str:
        """Use Gemini to intelligently classify and route queries"""
        try:
            # Get available subagent descriptions
            subagent_descriptions = []
            for name, subagent in self.subagents.items():
                capabilities = subagent.get_capabilities()
                subagent_descriptions.append(f"- **{name}**: {capabilities.get('description', 'No description')}")
            
            routing_prompt = f"""You are a query router for an agricultural AI assistant. Analyze the user's query and determine which specialized agent should handle it.

Available Agents:
{chr(10).join(subagent_descriptions)}

User Query: "{query}"

Instructions:
1. Analyze the query content and intent carefully
2. Consider the user's specific needs and requirements
3. Choose the MOST APPROPRIATE single agent for this query
4. For video/tutorial requests: Use youtube agent
5. For weather/climate queries: Use weather agent  
6. For market/price queries: Use market agent
7. For general knowledge/information: Use knowledge agent

Response with ONLY the agent name (weather, youtube, market, or knowledge):"""

            # Get routing decision from Gemini
            routing_message = HumanMessage(content=routing_prompt)
            response = await self.routing_llm.ainvoke([routing_message])
            
            # # Extract agent name from response
            agent_choice = re.search(r'\b(weather|youtube|market|knowledge)\b', response.content.lower())
            agent_choice = agent_choice.group(1) if agent_choice else response.content.strip().lower()
            
            # Validate and clean the response
            valid_agents = [a.lower() for a in self.subagents.keys()]
            
            # Direct match
            
            if agent_choice in valid_agents:
                logger.info(f"🎯 Gemini routed '{query[:50]}...' -> {agent_choice}")
                return agent_choice
            
            # Partial match
            for agent in valid_agents:
                if agent in agent_choice:
                    logger.info(f"🎯 Gemini routed (partial match) '{query[:50]}...' -> {agent}")
                    return agent
            
            # Fallback to keyword-based routing if Gemini response is unclear
            logger.warning(f"⚠️ Gemini routing unclear: '{agent_choice}', falling back to keyword matching")
            return self._fallback_keyword_routing(query)
            
        except Exception as e:
            logger.error(f"Error in Gemini routing: {e}")
            # Fallback to keyword-based routing
            return self._fallback_keyword_routing(query)
    
    def _fallback_keyword_routing(self, query: str) -> str:
        """Fallback keyword-based routing when Gemini routing fails"""
        query_lower = query.lower()
        
        # Weather-related keywords (check early and prioritize)
        if any(keyword in query_lower for keyword in [
            'weather', 'temperature', 'rainfall', 'humidity', 'climate', 'forecast',
            'rain', 'sunny', 'cloudy', 'storm', 'wind', 'district weather', 'imd'
        ]):
            return 'weather' if 'weather' in self.subagents else 'knowledge'
        
        # Video/tutorial requests
        elif any(keyword in query_lower for keyword in [
            'video', 'youtube', 'tutorial', 'show me', 'watch', 'demonstration',
            'learning video', 'educational video', 'farming video', 'tips video'
        ]):
            return 'youtube' if 'youtube' in self.subagents else 'knowledge'
        
        # Market-related keywords
        elif any(keyword in query_lower for keyword in [
            'price', 'market', 'commodity', 'cost', 'rate', 'trading', 'agmarknet',
            'mandi', 'wholesale', 'retail', 'crop price', 'agricultural price'
        ]):
            return 'market' if 'market' in self.subagents else 'knowledge'
        
        # Default to knowledge base
        else:
            return 'knowledge'

    def _create_custom_supervisor_node(self):
        """Create a custom supervisor node when create_react_agent is not available"""
        async def supervisor_node_func(state: MessagesState):
            try:
                # Get the last user message
                messages = state.get("messages", [])
                if not messages:
                    return {"messages": [AIMessage(content="No message to process", name="supervisor")]}
                
                # Find the most recent human message (the actual user query)
                user_message = None
                for msg in reversed(messages):
                    if hasattr(msg, 'type') and msg.type == 'human':
                        user_message = msg.content
                        break
                    elif isinstance(msg, HumanMessage):
                        user_message = msg.content
                        break
                    elif isinstance(msg, dict) and msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        break
                
                # Fallback to the last message if no human message found
                if not user_message and messages:
                    last_msg = messages[-1]
                    user_message = getattr(last_msg, 'content', str(last_msg))
                
                if not user_message:
                    user_message = "No user message found"
                
                # Clean up the user message - remove any context prefix
                if "Context from recent conversation:" in user_message:
                    # Extract just the current question
                    parts = user_message.split("Current question:")
                    if len(parts) > 1:
                        user_message = parts[-1].strip()
                        # Clean up any trailing instructions
                        user_message = user_message.split("Provide video recommendations")[0].strip()
                        user_message = user_message.rstrip('.')
                
                logger.info(f"🎯 Supervisor analyzing query: {user_message[:100]}...")
                
                # Route to appropriate subagent using Gemini
                subagent_name = await self._classify_query_with_gemini(user_message)
                
                logger.info(f"📋 Supervisor routing to: {subagent_name}")
                
                # Create clean task message (just the user query, no context)
                clean_task = user_message.strip()
                
                # Create transfer message
                transfer_message = AIMessage(
                    content=f"Routing to {subagent_name} agent",
                    name="supervisor"
                )
                
                # Create a clean task message for the subagent
                task_message = HumanMessage(content=clean_task)
                
                return {
                    "messages": [transfer_message, task_message],
                    "next_agent": f"{subagent_name}_agent"
                }
                
            except Exception as e:
                logger.error(f"Error in supervisor node: {e}")
                error_message = AIMessage(
                    content=f"I encountered an error analyzing your request: {str(e)}",
                    name="supervisor"
                )
                return {"messages": [error_message]}
        
        # Set a unique name for the function
        supervisor_node_func.__name__ = "supervisor_node_func"
        return supervisor_node_func

    def _generate_task_description(self, query: str, subagent_name: str) -> str:
        """Generate a clear task description for the subagent"""
        base_description = f"Please help with this query: {query}"
        
        if subagent_name == 'weather':
            return f"Provide weather information for: {query}. Include current conditions, forecasts, and relevant meteorological data."
        elif subagent_name == 'market':
            return f"Provide market price and commodity information for: {query}. Include current prices, trends, and market data."
        elif subagent_name == 'youtube':
            return f"Find relevant educational videos for: {query}. Provide video recommendations with descriptions."
        else:  # knowledge
            return f"Provide comprehensive information about: {query}. Search knowledge base and provide detailed, accurate information."
    
    def _create_subagent_handoff_tools(self):
        """Create handoff tools for each subagent (only used with create_react_agent)"""
        if not LANGGRAPH_REACT_AVAILABLE:
            return []
            
        handoff_tools = []
        
        def create_handoff_tool(agent_name: str, description: str):
            name = f"transfer_to_{agent_name}"
            
            @tool(name, description=description)
            def handoff_tool(
                task_description: Annotated[
                    str,
                    "Clear description of what the agent should do, including all relevant context.",
                ],
                state: Annotated[MessagesState, InjectedState] if InjectedState else MessagesState,
                tool_call_id: Annotated[str, InjectedToolCallId],
            ) -> Command:
                # Create tool message for the supervisor
                tool_message = ToolMessage(
                    content=f"Successfully transferred to {agent_name}",
                    name=name,
                    tool_call_id=tool_call_id,
                )
                
                # Create task message for the subagent
                task_message = HumanMessage(content=task_description)
                agent_input = {"messages": [task_message]}
                
                return Command(
                    goto=[Send(f"{agent_name}_agent", agent_input)],
                    update={"messages": state.get("messages", []) + [tool_message]}
                )
            
            return handoff_tool
        
        # Create handoff tools for each subagent
        if 'weather' in self.subagents:
            handoff_tools.append(create_handoff_tool(
                'weather',
                'Assign weather-related tasks to the weather agent. Use for weather forecasts, climate data, temperature, rainfall, and meteorological information.'
            ))
        
        if 'knowledge' in self.subagents:
            handoff_tools.append(create_handoff_tool(
                'knowledge', 
                'Assign knowledge and research tasks to the knowledge agent. Use for general information, policies, schemes, agricultural knowledge, and document searches.'
            ))
        
        if 'youtube' in self.subagents:
            handoff_tools.append(create_handoff_tool(
                'youtube',
                'Assign video search tasks to the youtube agent. Use when user asks for videos, tutorials, or educational content.'
            ))
        
        if 'market' in self.subagents:
            handoff_tools.append(create_handoff_tool(
                'market',
                'Assign market price and commodity tasks to the market agent. Use for agricultural prices, market rates, and commodity information.'
            ))
        
        return handoff_tools
    
    def _create_subagent_node(self, subagent_name: str, subagent):
        """Create a LangGraph node for a subagent"""
        async def subagent_node_func(state: MessagesState):
            try:
                # Extract the task from the last message
                last_message = state["messages"][-1]
                query = last_message.content if hasattr(last_message, 'content') else str(last_message)
                
                logger.info(f"🔄 Processing query with {subagent_name}: {query[:100]}...")
                
                # For YouTube subagent, trust our intelligent routing
                # The subagent itself is now more flexible and will handle the query appropriately
                
                # Process with subagent
                result = subagent.process_query(query)
                
                if result['success']:
                    response_message = AIMessage(
                        content=result['summary'],
                        name=f"{subagent_name}_agent"
                    )
                    logger.info(f"✅ {subagent_name} completed successfully")
                else:
                    response_message = AIMessage(
                        content=f"I encountered an error: {result.get('error', 'Unknown error')}",
                        name=f"{subagent_name}_agent"
                    )
                    logger.error(f"❌ {subagent_name} failed: {result.get('error')}")
                
                return {"messages": [response_message]}
                
            except Exception as e:
                logger.error(f"Error in {subagent_name} node: {e}")
                error_message = AIMessage(
                    content=f"I encountered an error processing your request: {str(e)}",
                    name=f"{subagent_name}_agent"
                )
                return {"messages": [error_message]}
        
        # Set a unique name for the function to avoid conflicts
        subagent_node_func.__name__ = f"{subagent_name}_node_func"
        return subagent_node_func
    
    def _create_langgraph_supervisor(self):
        """Create LangGraph supervisor with subagent integration"""
        if self.supervisor_graph is not None:
            logger.info("LangGraph supervisor already exists, skipping creation")
            return
            
        try:
            # Create the graph
            graph_builder = StateGraph(MessagesState)
            
            # First, add the supervisor node
            if LANGGRAPH_REACT_AVAILABLE:
                logger.info("Using create_react_agent for supervisor")

                # Create handoff tools
                # handoff_tools = self._create_subagent_handoff_tools()
                
                # Create supervisor agent
                supervisor_agent = create_react_agent(
                    model=self.routing_llm,  # Use routing LLM for supervisor
                    # tools=handoff_tools,
                    prompt=self._get_supervisor_system_message(),
                    name="supervisor"
                )
                
                # Add supervisor node
                available_agents = [f"{name}_agent" for name in self.subagents.keys()]
                graph_builder.add_node(
                    supervisor_agent, 
                    destinations=available_agents + [END]
                )
                
                # Add entry edge
                graph_builder.add_edge(START, "supervisor")
                
                # Add subagent nodes and return edges
                for name, subagent in self.subagents.items():
                    agent_name = f"{name}_agent"
                    subagent_node = self._create_subagent_node(name, subagent)
                    graph_builder.add_node(subagent_node, name=agent_name)
                    graph_builder.add_edge(agent_name, "supervisor")
                    logger.info(f"Added subagent node and edge: {agent_name}")
                
            else:
                logger.info("Using custom supervisor node implementation")
                # Create custom supervisor node
                supervisor_node = self._create_custom_supervisor_node()
                graph_builder.add_node("supervisor", supervisor_node)
                logger.info("Added supervisor node")
                
                # Add all subagent nodes FIRST - store the names for later reference
                subagent_node_names = []
                for name, subagent in self.subagents.items():
                    agent_name = f"{name}_agent"
                    subagent_node = self._create_subagent_node(name, subagent)
                    graph_builder.add_node(agent_name, subagent_node)
                    subagent_node_names.append(agent_name)
                    logger.info(f"Added subagent node: {agent_name}")
                
                # Add the START edge
                graph_builder.add_edge(START, "supervisor")
                logger.info("Added edge: START -> supervisor")
                
                # Create a routing function for conditional edges
                async def route_to_agent(state: MessagesState):
                    """Route to the appropriate agent based on supervisor decision"""
                    # Check if supervisor set a next_agent
                    if "next_agent" in state:
                        next_agent = state["next_agent"]
                        logger.info(f"Routing to: {next_agent}")
                        return next_agent
                    
                    # Fallback: use Gemini to analyze the last message
                    messages = state.get("messages", [])
                    if messages:
                        # Find the actual user query
                        user_query = None
                        for msg in reversed(messages):
                            if isinstance(msg, HumanMessage) and "Context from recent conversation" not in str(msg.content):
                                user_query = msg.content
                                break
                        
                        if user_query:
                            # Use Gemini routing as fallback
                            agent_name = await self._classify_query_with_gemini(user_query)
                            return f"{agent_name}_agent" if f"{agent_name}_agent" in subagent_node_names else subagent_node_names[0]
                    
                    return subagent_node_names[0] if subagent_node_names else END  # Default fallback
                
                # Add conditional edges from supervisor to subagents
                graph_builder.add_conditional_edges(
                    "supervisor",
                    route_to_agent,
                    subagent_node_names + [END]
                )
                logger.info(f"Added conditional edges from supervisor to: {subagent_node_names}")
                
                # Add edges from each subagent back to END (instead of supervisor to avoid loops)
                for agent_name in subagent_node_names:
                    graph_builder.add_edge(agent_name, END)
                    logger.info(f"Added edge: {agent_name} -> END")
            
            # Try to compile the graph
            logger.info("Attempting to compile the graph...")
            self.supervisor_graph = graph_builder.compile()
            
            logger.info("🎯 LangGraph supervisor created successfully")
            logger.info(f"📊 Available agents: {list(self.subagents.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to create LangGraph supervisor: {e}")
            logger.error(f"Subagents available: {list(self.subagents.keys())}")
            
            # Try a fallback to the original subagent architecture
            logger.info("Falling back to direct subagent routing...")
            self.use_langgraph_supervisor = False
            
            raise RuntimeError(f"LangGraph supervisor creation failed: {e}")
    
    def _get_supervisor_system_message(self) -> str:
        """Get system message for the supervisor"""
        today = date.today()
        today_str = today.strftime("%d-%m-%Y")
        
        available_agents = []
        for name in self.subagents.keys():
            if name == 'weather':
                available_agents.append("- **Weather Agent**: For weather forecasts, climate data, temperature, rainfall, and meteorological information")
            elif name == 'knowledge':
                available_agents.append("- **Knowledge Agent**: For general information, policies, schemes, agricultural knowledge, and document searches")
            elif name == 'youtube':
                available_agents.append("- **YouTube Agent**: For video searches, tutorials, and educational content")
            elif name == 'market':
                available_agents.append("- **Market Agent**: For agricultural prices, market rates, and commodity information")
        
        agents_list = "\n".join(available_agents)
        
        return f"""Today's date is {today_str}.

You are an intelligent supervisor managing specialized agents for agricultural and informational queries.

**Available Agents:**
{agents_list}

**Instructions:**
1. **Analyze each query intelligently** to determine which agent can best handle it
2. **Assign work to ONE agent at a time** - do not call agents in parallel
3. **Provide clear, detailed task descriptions** when transferring to agents
4. **Do not do any work yourself** - always delegate to the appropriate specialist agent
5. **Be smart about routing**: 
   - Video/tutorial requests -> YouTube agent
   - Weather/climate queries -> Weather agent
   - Market/price queries -> Market agent
   - General information -> Knowledge agent
6. **Context matters**: Consider the user's intent, not just keywords
7. **Be flexible**: If a query could fit multiple agents, choose the most specific one

**Task Description Guidelines:**
- Include all relevant context from the user's query
- Specify what information is needed
- Mention any specific requirements or constraints
- Be clear about the expected output format

Choose the most appropriate agent based on intelligent analysis of the query content and delegate the task with a comprehensive description."""
    
    def _initialize_tools(self):
        """Initialize tools for backward compatibility"""
        self.tools = [
            rag_tool,
            weather_tool,
            weather_districts_tool,
            youtube_search_tool,
            get_market_price,
            list_market_commodities,
            list_market_states,
        ]
        
        valid_tools = []
        for tool in self.tools:
            try:
                if hasattr(tool, 'name') and hasattr(tool, 'description'):
                    valid_tools.append(tool)
                    logger.info(f"✅ Tool validated: {tool.name}")
                else:
                    logger.warning(f"⚠️ Tool missing required attributes: {tool}")
            except Exception as e:
                logger.error(f"❌ Tool validation failed: {tool} - {e}")
        
        self.tools = valid_tools
        logger.info(f"Initialized {len(self.tools)} tools: {[t.name for t in self.tools]}")
    
    def _initialize_agent(self):
        """Initialize traditional agent for backward compatibility"""
        try:
            callbacks = [StdOutCallbackHandler()] if self.config['verbose'] else []
            
            agent_kwargs = {
                'system_message': self._get_traditional_system_message()
            }
            
            self.agent_executor = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=self.config['verbose'],
                memory=self.memory,
                agent_kwargs=agent_kwargs,
                callbacks=callbacks,
                max_iterations=self.config['max_iterations'],
                max_execution_time=self.config['max_execution_time'],
                handle_parsing_errors=True,
                return_intermediate_steps=False
            )
            
            logger.info("🤖 Traditional agent executor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise RuntimeError(f"Agent initialization failed: {e}")
    
    def _get_traditional_system_message(self) -> str:
        """Get system message for traditional agent"""
        today = date.today()
        today_str = today.strftime("%d-%m-%Y")
        
        return f"""Today's date is {today_str}.
You are a helpful AI assistant with access to multiple specialized tools for providing information about weather, agricultural market prices, and knowledge base queries.

**Available Tools:**
- **Knowledge Search (RAG)**: Search documentation, policies, and knowledge bases
- **Weather Information**: Get current weather and forecasts for Indian districts (IMD data)
- **Market Prices**: Get agricultural commodity prices from AgMarkNet for Indian markets
- **YouTube Search**: Find educational and agricultural videos

**Guidelines:**
1. **Always use appropriate tools** for specific queries rather than relying on general knowledge
2. **Be specific and accurate** in your responses
3. **Format responses clearly** using markdown when helpful
4. **Handle errors gracefully** and provide helpful suggestions
5. **For weather queries**: Use district names (e.g., "Bangalore Urban", "Mumbai")
6. **For market queries**: Use commodity and state names (e.g., "wheat prices in Karnataka")
7. **Provide context** about data sources and limitations when relevant

You should be helpful, accurate, and informative while being concise and well-structured in your responses."""
    
    async def initialize(self):
        """Initialize the complete orchestrator"""
        if self.is_initialized:
            logger.info("Orchestrator already initialized")
            return
        
        try:
            logger.info("🚀 Starting LangGraph supervisor orchestrator initialization...")
            
            # Step 1: Validate environment
            logger.info("1/6 Validating environment...")
            self._validate_environment()
            
            # Step 2: Initialize LLM
            logger.info("2/6 Initializing LLM...")
            self._initialize_llm()
            
            # Step 3: Initialize memory
            logger.info("3/6 Initializing memory...")
            self._initialize_memory()
            
            # Step 4: Initialize subagents
            logger.info("4/6 Initializing subagents...")
            self._initialize_subagents()
            
            # Step 5: Create LangGraph supervisor or traditional setup
            if self.use_langgraph_supervisor:
                logger.info("5/6 Creating LangGraph supervisor...")
                self._create_langgraph_supervisor()
            else:
                logger.info("5/6 Initializing tools...")
                self._initialize_tools()
            
            # Step 6: Initialize traditional agent if needed
            if not self.use_langgraph_supervisor:
                logger.info("6/6 Initializing traditional agent...")
                self._initialize_agent()
            else:
                logger.info("6/6 Skipping traditional agent (using LangGraph supervisor)")
            
            self.is_initialized = True
            
            if self.use_langgraph_supervisor:
                logger.info("✅ LangGraph supervisor orchestrator initialization completed!")
                logger.info(f"📊 Active subagents: {list(self.subagents.keys())}")
                logger.info("🧠 Using Gemini-powered intelligent routing")
            else:
                logger.info("✅ Traditional orchestrator initialization completed!")
                logger.info(f"📊 Active tools: {[t.name for t in self.tools]}")
            
            # Set global variables for backward compatibility
            global agent_executor, agent_memory
            agent_executor = self.agent_executor
            agent_memory = self.memory
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            raise
    
    async def query(self, message: str, **kwargs) -> Dict[str, Any]:
        """Execute a query using LangGraph supervisor or traditional agent"""
        if not self.is_initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        
        try:
            logger.info(f"🔍 Processing query: {message[:100]}...")
            
            if self.use_langgraph_supervisor and self.supervisor_graph:
                # Use LangGraph supervisor with Gemini routing
                logger.info("🧠 Using LangGraph supervisor with Gemini routing")
                
                # Create initial state
                initial_state = {
                    "messages": [HumanMessage(content=message)]
                }
                
                # Stream through the graph
                final_state = None
                agent_used = None
                supervisor_messages = []
                
                try:
                    async for chunk in self.supervisor_graph.astream(initial_state):
                        final_state = chunk
                        logger.info(f"Graph chunk: {list(chunk.keys())}")
                        
                        # Track which agent was used and collect supervisor messages
                        for node_name, node_state in chunk.items():
                            if node_name.endswith('_agent') and node_name != 'supervisor':
                                agent_used = node_name.replace('_agent', '')
                                logger.info(f"Agent {agent_used} executed with state keys: {list(node_state.keys())}")
                                
                                # Log the actual response from the agent
                                if 'messages' in node_state:
                                    for msg in node_state['messages']:
                                        content = getattr(msg, 'content', str(msg))
                                        logger.info(f"Agent {agent_used} response content length: {len(content)}")
                                        logger.info(f"Agent {agent_used} response preview: {content[:200]}...")
                                        
                            elif node_name == 'supervisor':
                                if 'messages' in node_state:
                                    supervisor_messages = node_state['messages']
                                    logger.info(f"Supervisor messages count: {len(supervisor_messages)}")
                
                except Exception as stream_error:
                    logger.error(f"Error during graph streaming: {stream_error}")
                    return {
                        'success': False,
                        'response': f"I encountered an error processing your request: {stream_error}",
                        'error': str(stream_error)
                    }
                
                if final_state:
                    # Try to get response from different possible locations
                    response = None
                    
                    # First, look for the actual subagent response (not supervisor routing messages)
                    if final_state:
                        # Look for the subagent that was used
                        subagent_response = None
                        
                        # Check each node in the final state
                        for node_name, node_state in final_state.items():
                            # Skip supervisor node, look for actual subagent responses
                            if node_name.endswith('_agent') and node_name != 'supervisor':
                                if 'messages' in node_state and node_state['messages']:
                                    for msg in node_state['messages']:
                                        if hasattr(msg, 'content') and msg.content.strip():
                                            content = msg.content.strip()
                                            # Make sure it's not just echoing the query or an error
                                            if (content != message and len(content) > len(message) 
                                                and not content.startswith("I encountered an error")):
                                                subagent_response = content
                                                break
                                        elif isinstance(msg, dict) and msg.get('content'):
                                            content = msg['content'].strip()
                                            if (content != message and len(content) > len(message)
                                                and not content.startswith("I encountered an error")):
                                                subagent_response = content
                                                break
                                
                                if subagent_response:
                                    response = subagent_response
                                    break
                    
                    # If still no good response, check for error messages that we can handle gracefully
                    if not response and final_state:
                        for node_name, node_state in final_state.items():
                            if node_name.endswith('_agent'):
                                if 'messages' in node_state and node_state['messages']:
                                    for msg in node_state['messages']:
                                        content = getattr(msg, 'content', str(msg))
                                        if content and content.strip():
                                            response = content.strip()
                                            break
                                if response:
                                    break
                    
                    # Final fallback response
                    if not response or response == message:
                        logger.warning("No proper response found, using fallback")
                        response = "I processed your request but encountered an issue generating a proper response. Please try rephrasing your question or being more specific about what you need."
                    
                    logger.info(f"✅ LangGraph supervisor completed successfully")
                    return {
                        'success': True,
                        'response': response,
                        'subagent_used': agent_used,
                        'architecture': 'langgraph_supervisor_gemini',
                        'error': None
                    }
                
                # Fallback response
                return {
                    'success': False,
                    'response': "I encountered an issue processing your query with the supervisor.",
                    'error': "No final state received from supervisor"
                }
            
            elif not self.use_langgraph_supervisor and self.agent_executor:
                # Use traditional agent
                logger.info("🤖 Using traditional agent")
                result = self.agent_executor.run(input=message)
                logger.info("✅ Traditional agent completed successfully")
                
                return {
                    'success': True,
                    'response': result,
                    'architecture': 'traditional',
                    'error': None
                }
            
            else:
                raise RuntimeError("No valid execution method available")
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            return {
                'success': False,
                'response': f"I encountered an error processing your query: {e}",
                'error': str(e)
            }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about the orchestrator"""
        if not self.is_initialized:
            return {'error': 'Orchestrator not initialized'}
        
        info = {
            'architecture': 'langgraph_supervisor_gemini' if self.use_langgraph_supervisor else 'traditional',
            'total_subagents': len(self.subagents),
            'subagents': [name for name in self.subagents.keys()],
            'config': self.config,
            'routing_method': 'gemini_ai' if self.use_langgraph_supervisor else 'keyword_based'
        }
        
        if self.use_langgraph_supervisor:
            info['supervisor_graph'] = 'initialized' if self.supervisor_graph else 'not_initialized'
            info['routing_llm'] = 'initialized' if self.routing_llm else 'not_initialized'
        else:
            info['tools'] = [tool.name for tool in self.tools] if self.tools else []
            info['agent'] = 'initialized' if self.agent_executor else 'not_initialized'
        
        return info
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the orchestrator"""
        status = {
            'orchestrator': 'healthy' if self.is_initialized else 'not_initialized',
            'architecture': 'langgraph_supervisor_gemini' if self.use_langgraph_supervisor else 'traditional',
            'llm': 'healthy' if self.llm else 'not_initialized',
            'routing_llm': 'healthy' if self.routing_llm else 'not_initialized',
            'memory': 'healthy' if self.memory else 'disabled',
            'subagents': len(self.subagents) if self.subagents else 0
        }
        
        if self.use_langgraph_supervisor:
            status['supervisor_graph'] = 'healthy' if self.supervisor_graph else 'not_initialized'
        else:
            status['agent'] = 'healthy' if self.agent_executor else 'not_initialized'
            status['tools'] = len(self.tools) if self.tools else 0
        
        return {
            'status': status,
            'timestamp': str(asyncio.get_event_loop().time()),
            'config': self.config
        }


# Create alias for backward compatibility
AgentOrchestrator = LangGraphSupervisorOrchestrator

# Global orchestrator instance
_orchestrator = None

async def get_orchestrator() -> LangGraphSupervisorOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LangGraphSupervisorOrchestrator()
        await _orchestrator.initialize()
    return _orchestrator

# Legacy functions for backward compatibility
async def init_orchestrator():
    """Legacy initialization function"""
    logger.info("Using legacy init_orchestrator() - consider using get_orchestrator()")
    orchestrator = await get_orchestrator()
    
    # Set global variables
    global agent_executor, agent_memory
    agent_executor = orchestrator.agent_executor
    agent_memory = orchestrator.memory
    
    if orchestrator.use_langgraph_supervisor:
        print("✅ LangGraph supervisor with Gemini routing initialized with subagents:", list(orchestrator.subagents.keys()))
    else:
        print("✅ Traditional agent initialized with tools:", [t.name for t in orchestrator.tools])

async def query_agent(message: str) -> str:
    """Legacy query function"""
    orchestrator = await get_orchestrator()
    result = await orchestrator.query(message)
    
    if result['success']:
        return result['response']
    else:
        return f"Error: {result['error']}"

# Health check endpoint helper
async def health_check():
    """Health check for the orchestrator"""
    try:
        orchestrator = await get_orchestrator()
        return orchestrator.health_check()
    except Exception as e:
        return {
            'status': {'orchestrator': 'error', 'error': str(e)},
            'timestamp': str(asyncio.get_event_loop().time())
        }