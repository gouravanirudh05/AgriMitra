# orchestrator.py
import os
import logging
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import dotenv
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import StdOutCallbackHandler
from tools.youtube_search_tool import youtube_search_tool

# import datetime
from datetime import date
dotenv.load_dotenv()
# Import all tools
from tools.rag_tool import rag_tool
from tools.weather_tool import weather_tool, weather_districts_tool
#from ..tools.market_price import market_price_tool, list_market_commodities, list_market_states
from tools.agri_market import get_market_price,list_market_commodities,list_market_states
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global agent executor
agent_executor = None
agent_memory = None

class AgentOrchestrator:
    """Enhanced orchestrator for managing LangChain agent with multiple tools"""
    
    def __init__(self):
        self.agent_executor = None
        self.memory = None
        self.llm = None
        self.tools = []
        self.is_initialized = False
        
        # Configuration
        self.config = {
            'model': os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
            'temperature': float(os.getenv('AGENT_TEMPERATURE', '0')),
            'memory_window': int(os.getenv('MEMORY_WINDOW', '10')),
            'max_iterations': int(os.getenv('MAX_ITERATIONS', '15')),
            'max_execution_time': int(os.getenv('MAX_EXECUTION_TIME', '60')),
            'verbose': os.getenv('AGENT_VERBOSE', 'true').lower() == 'true'
        }
    
    def _validate_environment(self):
        """Validate required environment variables and dependencies"""
        required_env_vars = ['GOOGLE_API_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {missing_vars}")
        
        # Validate optional configurations
        optional_configs = {
            'IMD_CODES_FILE': 'datasets/IMDCodes.csv',
            'AGMARKNET_DATA_DIR': 'datasets',
            'WEATHER_DOWNLOAD_DIR': 'downloads/weather',
            'WEATHER_CACHE_DAYS': '30'
        }
        
        for var, default in optional_configs.items():
            if not os.getenv(var):
                logger.info(f"Using default for {var}: {default}")
        
        # Create necessary directories
        dirs_to_create = [
            Path(os.getenv('AGMARKNET_DATA_DIR', 'datasets')),
            Path(os.getenv('WEATHER_DOWNLOAD_DIR', 'downloads/weather')),
            Path('downloads'),
            Path('logs')
        ]
        
        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
    def _initialize_llm(self):
        """Initialize the Language Model"""
        try:
            # Fixed safety settings - using numeric values instead of string constants
            # Safety setting values: 0=BLOCK_NONE, 1=BLOCK_ONLY_HIGH, 2=BLOCK_MEDIUM_AND_ABOVE, 3=BLOCK_LOW_AND_ABOVE
            # Harm category values: 7=HARASSMENT, 8=HATE_SPEECH, 9=SEXUALLY_EXPLICIT, 10=DANGEROUS_CONTENT
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
            logger.info(f"LLM initialized: {self.config['model']}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            # Try alternative initialization without safety settings
            try:
                logger.info("Attempting LLM initialization without safety settings...")
                self.llm = ChatGoogleGenerativeAI(
                    model=self.config['model'],
                    temperature=self.config['temperature'],
                    convert_system_message_to_human=True
                )
                logger.info(f"LLM initialized without safety settings: {self.config['model']}")
            except Exception as e2:
                logger.error(f"Failed to initialize LLM without safety settings: {e2}")
                raise RuntimeError(f"LLM initialization failed: {e2}")
    
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
            # Continue without memory if initialization fails
            self.memory = None
    
    def _initialize_tools(self):
        """Initialize and validate all tools"""
        self.tools = [
            # RAG Tool
            rag_tool,
            
            # Weather Tools
            weather_tool,
            weather_districts_tool,
            youtube_search_tool,
            # Market Price Tools
            get_market_price,
            list_market_commodities,
            list_market_states,
        ]
        
        # Validate tools
        valid_tools = []
        for tool in self.tools:
            try:
                # Basic validation - check if tool has required attributes
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
        """Initialize the LangChain agent"""
        try:
            # Callbacks
            callbacks = [StdOutCallbackHandler()] if self.config['verbose'] else []
            
            # Agent configuration
            agent_kwargs = {
                'system_message': self._get_system_message()
            }
            
            # Initialize agent
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
            
            logger.info("🤖 Agent executor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise RuntimeError(f"Agent initialization failed: {e}")
    
    def _get_system_message(self) -> str:
        """Get system message for the agent"""
        # get today's date. 
        today = date.today()
        today_str = today.strftime("%d-%m-%Y")
        return """  
        Today's date is {today_str}.
        You are a helpful AI assistant with access to multiple specialized tools for providing information about weather, agricultural market prices, and knowledge base queries.

**Available Tools:**
- **Knowledge Search (RAG)**: Search documentation, policies, and knowledge bases
- **Weather Information**: Get current weather and forecasts for Indian districts (IMD data)
- **Market Prices**: Get agricultural commodity prices from AgMarkNet for Indian markets

**Guidelines:**
1. **Always use appropriate tools** for specific queries rather than relying on general knowledge
2. **Be specific and accurate** in your responses
3. **Format responses clearly** using markdown when helpful
4. **Handle errors gracefully** and provide helpful suggestions
5. **For weather queries**: Use district names (e.g., "Bangalore Urban", "Mumbai")
6. **For market queries**: Use commodity and state names (e.g., "wheat prices in Karnataka")
7. **Provide context** about data sources and limitations when relevant

**Response Format:**
- Use clear headings and bullet points
- Include relevant metadata (dates, sources)
- Provide actionable information when possible
- Suggest related queries when appropriate

You should be helpful, accurate, and informative while being concise and well-structured in your responses."""
    
    async def initialize(self):
        """Initialize the complete orchestrator"""
        if self.is_initialized:
            logger.info("Orchestrator already initialized")
            return
        
        try:
            logger.info("🚀 Starting orchestrator initialization...")
            
            # Step 1: Validate environment
            logger.info("1/5 Validating environment...")
            self._validate_environment()
            
            # Step 2: Initialize LLM
            logger.info("2/5 Initializing LLM...")
            self._initialize_llm()
            
            # Step 3: Initialize memory
            logger.info("3/5 Initializing memory...")
            self._initialize_memory()
            
            # Step 4: Initialize tools
            logger.info("4/5 Initializing tools...")
            self._initialize_tools()
            
            # Step 5: Initialize agent
            logger.info("5/5 Initializing agent...")
            self._initialize_agent()
            
            self.is_initialized = True
            logger.info("✅ Orchestrator initialization completed successfully!")
            
            # Set global variables for backward compatibility
            global agent_executor, agent_memory
            agent_executor = self.agent_executor
            agent_memory = self.memory
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            raise
    
    async def query(self, message: str, **kwargs) -> Dict[str, Any]:
        """Execute a query using the agent"""
        if not self.is_initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        
        try:
            logger.info(f"🔍 Processing query: {message[:100]}...")
            
            # Execute query
            result = self.agent_executor.run(
                input=message
            )
            
            logger.info("✅ Query processed successfully")
            
            return {
                'success': True,
                'response': result,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            return {
                'success': False,
                'response': None,
                'error': str(e)
            }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about available tools"""
        if not self.is_initialized:
            return {'error': 'Orchestrator not initialized'}
        
        tools_info = []
        for tool in self.tools:
            tools_info.append({
                'name': tool.name,
                'description': tool.description,
                'type': type(tool).__name__
            })
        
        return {
            'total_tools': len(self.tools),
            'tools': tools_info,
            'config': self.config
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the orchestrator"""
        status = {
            'orchestrator': 'healthy' if self.is_initialized else 'not_initialized',
            'llm': 'healthy' if self.llm else 'not_initialized',
            'memory': 'healthy' if self.memory else 'disabled',
            'agent': 'healthy' if self.agent_executor else 'not_initialized',
            'tools': len(self.tools) if self.tools else 0
        }
        
        return {
            'status': status,
            'timestamp': str(asyncio.get_event_loop().time()),
            'config': self.config
        }

# Global orchestrator instance
_orchestrator = None

async def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
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
    
    print("✅ Agent initialized with tools:", [t.name for t in orchestrator.tools])

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