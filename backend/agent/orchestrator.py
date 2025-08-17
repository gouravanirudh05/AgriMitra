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
from langchain_core.messages import convert_to_messages, HumanMessage, AIMessage, ToolMessage, SystemMessage

# Try to import create_react_agent, fall back to custom implementation
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import StdOutCallbackHandler

# Import subagents (keep existing imports)
from subagents.weather_subagent import WeatherSubAgent
from subagents.rag_subagent import RAGSubAgent
from subagents.youtube_subagent import YouTubeSubAgent
from subagents.market_subagent import MarketSubAgent
from subagents.fertilizer_subagent import FertilizerSubAgent
from subagents.image_subagent import ImageSubAgent
from langchain_core.tools import tool
from langgraph_supervisor.handoff import create_forward_message_tool
# Import tools for backward compatibility
from tools.rag_tool import rag_tool
from tools.weather_tool import weather_tool, weather_districts_tool
from tools.youtube_search_tool import youtube_search_tool
from tools.agri_market import get_market_price, list_market_commodities, list_market_states
from tools.fertilizer import get_recommendation
from tools.image_tool import plant_analysis_tool, plant_models_tool

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
print("LANGRRRRRRRRRRRRRRRRRRRRRR: ",LANGGRAPH_REACT_AVAILABLE)
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
            Path(os.getenv('WEATHER_DOWNLOAD_DIR', 'downloads')),
            Path('uploads'), 
            Path('models'),
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
                temperature=0.1,  # Slightly higher for routing decisions
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
                'image':ImageSubAgent(),
                # 'youtube': YouTubeSubAgent(),
                'market': MarketSubAgent(),
                'fertilizer': FertilizerSubAgent()
            }
            
            # Validate subagents
            valid_subagents = {}
            for name, subagent in self.subagents.items():
                try:
                    capabilities = subagent.get_capabilities()
                    if not hasattr(subagent, 'agent_executor') or subagent.agent_executor is None:
                        logger.warning(f"Subagent {name} missing agent_executor, creating placeholder")
                    # Create a minimal agent_executor if missing
                        subagent.agent_executor = subagent
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
4. For image analysis/plant disease queries: Use image agent
5. For video/tutorial requests: Use youtube agent
6. For weather/climate queries: Use weather agent  
7. For market/price queries: Use market agent
8. For fertilizer recommendations: Use fertilizer agent
9. For general knowledge/information: Use knowledge agent

Response with ONLY the agent name (weather,image, youtube, market, fertilizer, or knowledge):"""

            # Get routing decision from Gemini
            routing_message = HumanMessage(content=routing_prompt)
            response = await self.routing_llm.ainvoke([routing_message])
            
            # # Extract agent name from response
            agent_choice = re.search(r'\b(weather|image|youtube|market|knowledge|fertilizer)\b', response.content.lower())
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
            
            logger.warning(f"⚠️ Gemini routing unclear: '{agent_choice}', ending...")
            return END
            
        except Exception as e:
            logger.error(f"Error in Gemini routing: {e}")
            return END
    
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
                if subagent_name == END:
                    return {
                        'success': False,
                        'response': "I encountered an issue processing your query with the supervisor.",
                        'error': "No final state received from supervisor"
                    }
                
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
            if LANGGRAPH_REACT_AVAILABLE:
                logger.info("Using create_react_agent for supervisor")
                
                agent_objs = [sa.agent_executor for sa in self.subagents.values()]
                # Create supervisor agent
                forwarding_tool = create_forward_message_tool("supervisor")
                supervisor_agent = create_supervisor(
                    model=self.routing_llm,  # Use routing LLM for supervisor
                    agents=agent_objs,
                    prompt=self._get_supervisor_system_message(),
                    tools=[forwarding_tool],
                    name="supervisor",
                    output_mode = "last_message",
                    add_handoff_back_messages=False,
                    # add_handoff_messages=False,
                    handoff_tool_prefix="consult_with"
                )
                try:
                    supervisor_agent = supervisor_agent.compile()
                except Exception as e:
                    print("Error compiling supervisor agent:", e)
                
                # Try to compile the graph
                # logger.info("Attempting to compile the graph...")
                self.supervisor_graph = supervisor_agent
            
                
                logger.info("LangGraph supervisor created successfully")
                logger.info(f"Available agents: {list(self.subagents.keys())}")
            
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
            elif name == 'fertilizer':
                available_agents.append("- **Fertilizer Agent**: For fertilizer recommendations and information")
            elif name == 'image':
                available_agents.append("- **Image Agent**: For plant disease detection, crop analysis, and agricultural image diagnosis")

# The complete available agents section should look like:
        agents_list = "\n".join(available_agents)
        
        return f"""Today's date is {today_str}.

You are an intelligent supervisor managing specialized agents for agricultural and informational queries.

**Available Agents:**
{agents_list}

**Instructions:**
0. Always call the image agent first, if the image has been provided. 
1. **Analyze each query intelligently** to determine which agent can best handle it
2. You may assign work to **one or more agents** one after the other if the query spans multiple domains.
3. **Provide clear, detailed task descriptions** to each agent you call.
4. **Do not do any work yourself** - always delegate to the appropriate specialist agent
5. **Be smart about routing**: 
   - Video/tutorial requests -> YouTube agent
   - Weather/climate queries -> Weather agent
   - Market/price queries -> Market agent
   - General information -> Knowledge agent
6. **Context matters**: Consider the user's intent, not just keywords
7. **Be efficient**: if multiple agents are called, ensure their outputs together will fully answer the query.
8. **When to use multiple agents**:
   - If the query contains distinct sub-requests that fall under different agents.
   - If answering the query fully requires combining data from different domains.
**Task Description Guidelines:**
- Include all relevant context from the user's query
- Specify what information is needed
- Mention any specific requirements or constraints
- Be clear about the expected output format

**Handoff Rule (must follow):**
When sending a query to an agent:
1. Rewrite the user’s request into a **clear, agent-specific instruction**.
2. Remove unrelated details that are outside that agent’s domain.
3. Include:
   - The exact commodity/location/timeframe for Market Agent
   - The exact date/location/weather parameter for Weather Agent
   - The exact topic/title for YouTube Agent
   - The exact knowledge scope for Knowledge Agent
4. Never pass a query containing instructions unrelated to the chosen agent’s domain.

Routing Process (always follow):
1. Break the user query into separate sub-requests.
2. For each sub-request, identify domain keywords.
3. Send each sub-request only to its correct agent.
4. After getting sub-request from one of the agents, see what details you need, and send another sub-request to the another agent. Or if more context is needed from the user, ask them to provide more details.
5. MAKE SURE YOU HAVE CALLED ALL AGENTS AND HAVE RECEIVED ALL RESPONSES BEFORE COMBINING THEM. IF NOT CALL THEM AGAIN.
Once all necessary agent responses are collected, combine them into a single, concise, and informative final answer for the user answering all of their queries.
"""
    
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
            plant_analysis_tool,  
            plant_models_tool 
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
                logger.error("Langgraph not available, terminating")
                raise RuntimeError("Langgraph not available, terminating")
                # logger.info("6/6 Initializing traditional agent...")
            else:
                logger.info("6/6 Skipping traditional agent (using LangGraph supervisor)")
                logger.info("✅ LangGraph supervisor orchestrator initialization completed!")
                logger.info(f"📊 Active subagents: {list(self.subagents.keys())}")
                logger.info("🧠 Using Gemini-powered intelligent routing")
            
            self.is_initialized = True

            # Set global variables for backward compatibility
            global agent_executor, agent_memory
            agent_executor = self.agent_executor
            agent_memory = self.memory
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            raise
    
    async def query(self, message: str, **kwargs) -> Dict[str, Any]:
        """Execute a query using LangGraph supervisor or traditional agent"""
        user_context = kwargs.get("user_context", {})
        if not self.is_initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        image = kwargs.get('image')
        user_id = kwargs.get('user_id', 'default_user')
        conversation_id = kwargs.get('conversation_id', 'default_conv')
        
        if self.use_langgraph_supervisor and self.supervisor_graph:
            try:
                logger.info(f"🔍 Processing query: {message[:100]}...")
                result = self.supervisor_graph.invoke({
                    "messages": [
                        HumanMessage(content=f"CONVERSATIONID:{conversation_id}|User Context: User lives in state of {user_context['state']} and district of {user_context['district']}. His name is {user_context['name']}. Today's date is {date.today().strftime('%d-%m-%Y')}. {image!=None and 'Image data provided' or 'No image data provided'}."),
                        HumanMessage(content=message, image=image)
                    ]
                })
                logger.info(f"✅ LangGraph supervisor completed successfully")
                for m in result["messages"]:
                    m.pretty_print()
                assistant_messages = [m for m in result["messages"] if getattr(m, "content", None)]
                if assistant_messages:
                    final_message = '\n'.join([m.content for m in assistant_messages])
                else:
                    final_message = None

                return {
                    'success': True,
                    'response': final_message,
                    'subagent_used': None,
                    'architecture': 'langgraph_supervisor',
                    'error': None
                }
            except Exception as e:
                logger.error(f"❌ Query processing failed: {e}")
                return {
                    'success': False,
                    'response': f"I encountered an error processing your query: {e}",
                    'error': str(e)
                }
        else:
            raise RuntimeError("No valid execution method available")
    
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