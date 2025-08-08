# orchestrator.py (Modified for Subagent Architecture)
import os
import logging
from typing import Dict, Any, Optional, List
import asyncio
from pathlib import Path
import dotenv
from datetime import date
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import StdOutCallbackHandler

# Import subagents
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

class AgentOrchestrator:
    """Enhanced orchestrator for managing subagents instead of direct tools"""
    
    def __init__(self):
        self.subagents = {}
        self.llm = None
        self.memory = None
        self.agent_executor = None
        self.tools = []  # Keep for backward compatibility
        self.is_initialized = False
        self.use_subagents = True  # Flag to toggle between subagents and direct tools
        
        # Configuration
        self.config = {
            'model': os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
            'temperature': float(os.getenv('AGENT_TEMPERATURE', '0')),
            'memory_window': int(os.getenv('MEMORY_WINDOW', '10')),
            'max_iterations': int(os.getenv('MAX_ITERATIONS', '15')),
            'max_execution_time': int(os.getenv('MAX_EXECUTION_TIME', '60')),
            'verbose': os.getenv('AGENT_VERBOSE', 'true').lower() == 'true',
            'use_subagents': os.getenv('USE_SUBAGENTS', 'true').lower() == 'true'
        }
        
        self.use_subagents = self.config['use_subagents']
    
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
            Path('logs'),
            Path('subagents') if self.use_subagents else None
        ]
        
        for directory in [d for d in dirs_to_create if d is not None]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
    def _initialize_llm(self):
        """Initialize the Language Model"""
        try:
            # Fixed safety settings - using numeric values instead of string constants
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
    
    def _initialize_tools(self):
        """Initialize and validate all tools (for backward compatibility)"""
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
        """Initialize the LangChain agent (for backward compatibility)"""
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
    
    def _classify_query(self, query: str) -> str:
        """Classify query to determine which subagent should handle it"""
        query_lower = query.lower()
        
        # YouTube/Video-related keywords (check first with explicit video requests)
        explicit_video_keywords = [
            'show me video', 'find video', 'youtube video', 'watch video',
            'video tutorial', 'learning video', 'educational video', 
            'demonstration video', 'tutorial video', 'video about'
        ]
        
        # Weather-related keywords
        weather_keywords = [
            'weather', 'temperature', 'rainfall', 'humidity', 'climate', 'forecast',
            'rain', 'sunny', 'cloudy', 'storm', 'wind', 'district weather', 'imd'
        ]
        
        # Market-related keywords
        market_keywords = [
            'price', 'market', 'commodity', 'cost', 'rate', 'trading', 'agmarknet',
            'mandi', 'wholesale', 'retail', 'crop price', 'agricultural price'
        ]
        
        # Government scheme keywords (high priority for knowledge base)
        scheme_keywords = [
            'pm kisan', 'pradhan mantri', 'kisan samman nidhi', 'government scheme',
            'subsidy', 'yojana', 'policy', 'benefits', 'eligibility', 'application',
            'enrollment', 'registration', 'dbf', 'direct benefit transfer'
        ]
        
        # Knowledge/RAG-related keywords (broader category)
        knowledge_keywords = [
            'information', 'about', 'explain', 'what is', 'how does', 
            'farming', 'agriculture', 'crop', 'soil',
            'fertilizer', 'pest', 'organic', 'irrigation'
        ]
        
        # Check for explicit video requests first
        if any(keyword in query_lower for keyword in explicit_video_keywords):
            return 'youtube'
        
        # Check for government schemes (high priority)
        if any(keyword in query_lower for keyword in scheme_keywords):
            return 'knowledge'
        
        # Check for specific domain matches
        if any(keyword in query_lower for keyword in weather_keywords):
            return 'weather'
        elif any(keyword in query_lower for keyword in market_keywords):
            return 'market'
        elif any(keyword in query_lower for keyword in knowledge_keywords):
            return 'knowledge'
        
        # Context-based inference
        if any(word in query_lower for word in ['district', 'region', 'area']) and \
           any(word in query_lower for word in ['forecast', 'conditions']):
            return 'weather'
        
        if any(word in query_lower for word in ['state', 'karnataka', 'kerala', 'punjab']) and \
           any(word in query_lower for word in ['price', 'cost', 'rate']):
            return 'market'
        
        # Special handling for common question patterns
        if query_lower.startswith(('what is', 'explain', 'tell me about', 'how does', 'what are')):
            return 'knowledge'
        
        # Default to knowledge base for general queries
        return 'knowledge'
    
    async def _route_to_subagent(self, query: str) -> Dict[str, Any]:
        """Route query to appropriate subagent with fallback handling"""
        try:
            # Classify the query
            subagent_type = self._classify_query(query)
            
            logger.info(f"🎯 Routing query to {subagent_type} subagent")
            
            # Get the appropriate subagent
            subagent = self.subagents.get(subagent_type)
            if not subagent:
                raise ValueError(f"Subagent '{subagent_type}' not available")
            
            # Special check for YouTube subagent
            if subagent_type == 'youtube' and hasattr(subagent, 'should_handle_query'):
                if not subagent.should_handle_query(query):
                    logger.info("🔄 YouTube subagent declined query, routing to knowledge subagent")
                    result = self.subagents['knowledge'].process_query(query)
                    result['subagent_used'] = 'knowledge'
                    result['routing_confidence'] = 'redirected_from_youtube'
                    return result
            
            # Process query with subagent
            result = subagent.process_query(query)
            
            # Check if subagent suggests redirection
            if result.get('should_redirect'):
                redirect_to = result['should_redirect']
                logger.info(f"🔄 Subagent suggests redirect to {redirect_to}")
                
                if redirect_to in self.subagents:
                    redirect_result = self.subagents[redirect_to].process_query(query)
                    redirect_result['subagent_used'] = redirect_to
                    redirect_result['routing_confidence'] = f'redirected_from_{subagent_type}'
                    return redirect_result
            
            # Add routing metadata
            result['subagent_used'] = subagent_type
            result['routing_confidence'] = 'high'  # Could be enhanced with ML-based classification
            
            return result
            
        except Exception as e:
            logger.error(f"Error routing to subagent: {e}")
            # Fallback to knowledge subagent
            try:
                logger.info("🔄 Falling back to knowledge subagent")
                result = self.subagents['knowledge'].process_query(query)
                result['subagent_used'] = 'knowledge'
                result['routing_confidence'] = 'fallback'
                return result
            except Exception as e2:
                return {
                    'success': False,
                    'error': f"Routing failed: {e2}",
                    'subagent_used': 'none',
                    'raw_result': None,
                    'summary': f"I encountered an error processing your query: {e2}"
                }
    
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
            
            # Step 4: Initialize subagents or tools
            if self.use_subagents:
                logger.info("4/5 Initializing subagents...")
                self._initialize_subagents()
            else:
                logger.info("4/5 Initializing tools...")
                self._initialize_tools()
            
            # Step 5: Initialize agent (for backward compatibility)
            if not self.use_subagents:
                logger.info("5/5 Initializing agent...")
                self._initialize_agent()
            else:
                logger.info("5/5 Skipping agent initialization (using subagents)")
            
            self.is_initialized = True
            
            if self.use_subagents:
                logger.info("✅ Orchestrator initialization completed with subagent architecture!")
                logger.info(f"📊 Active subagents: {list(self.subagents.keys())}")
            else:
                logger.info("✅ Orchestrator initialization completed with tool architecture!")
                logger.info(f"📊 Active tools: {[t.name for t in self.tools]}")
            
            # Set global variables for backward compatibility
            global agent_executor, agent_memory
            agent_executor = self.agent_executor
            agent_memory = self.memory
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            raise
    
    async def query(self, message: str, **kwargs) -> Dict[str, Any]:
        """Execute a query using either subagents or the traditional agent"""
        if not self.is_initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        
        try:
            logger.info(f"🔍 Processing query: {message[:100]}...")
            
            if self.use_subagents:
                # Use subagent routing
                result = await self._route_to_subagent(message)
                
                if result['success']:
                    logger.info(f"✅ Query processed successfully by {result.get('subagent_used', 'unknown')} subagent")
                    return {
                        'success': True,
                        'response': result['summary'],
                        'subagent_used': result.get('subagent_used'),
                        'tool_used': result.get('tool_used'),
                        'raw_result': result.get('raw_result'),
                        'error': None
                    }
                else:
                    logger.error(f"❌ Subagent processing failed: {result.get('error')}")
                    return {
                        'success': False,
                        'response': result['summary'],
                        'error': result.get('error')
                    }
            
            else:
                # Use traditional agent
                result = self.agent_executor.run(input=message)
                logger.info("✅ Query processed successfully by traditional agent")
                
                return {
                    'success': True,
                    'response': result,
                    'error': None
                }
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            return {
                'success': False,
                'response': f"I encountered an error processing your query: {e}",
                'error': str(e)
            }
    
    def _get_system_message(self) -> str:
        """Get system message for the agent"""
        today = date.today()
        today_str = today.strftime("%d-%m-%Y")
        
        return f"""  
        Today's date is {today_str}.
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

**Response Format:**
- Use clear headings and bullet points
- Include relevant metadata (dates, sources)
- Provide actionable information when possible
- Suggest related queries when appropriate

You should be helpful, accurate, and informative while being concise and well-structured in your responses."""
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about available tools/subagents"""
        if not self.is_initialized:
            return {'error': 'Orchestrator not initialized'}
        
        if self.use_subagents:
            subagents_info = []
            for name, subagent in self.subagents.items():
                capabilities = subagent.get_capabilities()
                subagents_info.append({
                    'name': capabilities['name'],
                    'description': capabilities['description'],
                    'type': 'subagent',
                    'capabilities': capabilities
                })
            
            return {
                'architecture': 'subagents',
                'total_subagents': len(self.subagents),
                'subagents': subagents_info,
                'config': self.config
            }
        else:
            tools_info = []
            for tool in self.tools:
                tools_info.append({
                    'name': tool.name,
                    'description': tool.description,
                    'type': type(tool).__name__
                })
            
            return {
                'architecture': 'tools',
                'total_tools': len(self.tools),
                'tools': tools_info,
                'config': self.config
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the orchestrator"""
        status = {
            'orchestrator': 'healthy' if self.is_initialized else 'not_initialized',
            'architecture': 'subagents' if self.use_subagents else 'tools',
            'llm': 'healthy' if self.llm else 'not_initialized',
            'memory': 'healthy' if self.memory else 'disabled',
        }
        
        if self.use_subagents:
            status['subagents'] = len(self.subagents) if self.subagents else 0
            status['agent'] = 'disabled'
        else:
            status['agent'] = 'healthy' if self.agent_executor else 'not_initialized'
            status['tools'] = len(self.tools) if self.tools else 0
        
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
    
    if orchestrator.use_subagents:
        print("✅ Agent initialized with subagents:", list(orchestrator.subagents.keys()))
    else:
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