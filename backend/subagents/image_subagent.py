import os
import re
import logging
from typing import Dict, Any, Optional
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import StdOutCallbackHandler
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from app.store import IMGSTORE
# Import the image tools
from langchain.tools import tool
from tools.image_tool import plant_analysis_tool, plant_models_tool, analyze_plant_image
from langgraph.prebuilt import InjectedState, ToolNode
from typing_extensions import Annotated, TypedDict
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

image_subagent = None
@tool("plant_analysis_tool")
def process_query(state: Annotated[dict, InjectedState]) -> Dict[str, Any]:
    """Process image analysis query"""
    if image_subagent is not None:
        try:
            return image_subagent.process_query(state)
        except Exception as e:
            logger.error(f"Error processing image analysis query: {e}")
            return f"Error processing image analysis query"
    else:
        return "Something went wrong..."

class ImageSubAgent:
    """Subagent specialized in plant disease detection and image analysis"""
    
    def __init__(self):
        self.name = "Image Analysis Agent"
        self.description = "Specialized agent for plant disease detection, crop analysis, and agricultural image diagnosis"
        self.llm = None
        self.agent_executor = None
        self.memory = None
        self.tools = [process_query]
        self.capabilities = {
            'name': self.name,
            'description': self.description,
            'tools': [tool.name for tool in self.tools],
            'specializations': [
                'Plant disease detection',
                'Crop health analysis', 
                'Agricultural image diagnosis',
                'Disease identification',
                'Model-based predictions'
            ]
        }
        self._initialize()
    
    def _initialize(self):
        """Initialize the image analysis agent"""
        try:
            # Initialize LLM with system prompt directly
            system_prompt = self._get_system_message()
            
            self.llm = ChatGoogleGenerativeAI(
                model=os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
                temperature=0.1,  # Lower temperature for more consistent analysis
                safety_settings={
                    7: 0, 8: 0, 9: 0, 10: 0  # Disable safety filters for agricultural content
                },
                system=system_prompt  # Set system prompt directly on LLM
            )
            
            # Initialize memory - note: this won't be used with LangGraph agent but kept for compatibility
            # self.memory = ConversationBufferWindowMemory(
            #     k=5,  # Shorter memory for focused analysis
            #     memory_key="chat_history", 
            #     return_messages=True
            # )
            
            # Create the prompt template with system message
            prompt_template = SystemMessage(content=(system_prompt))
            
            # Initialize agent with only the required parameters
            self.agent_executor = create_react_agent(
                name="image-agent",
                model=self.llm,
                tools=self.tools,
                prompt=prompt_template  # Use prompt parameter for system instructions
            )
            
            logger.info("✅ Image subagent initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize image subagent: {e}")
            # Fallback: try without custom prompt
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model=os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
                    temperature=0.1,
                    safety_settings={
                        7: 0, 8: 0, 9: 0, 10: 0
                    }
                )
                
                self.agent_executor = create_react_agent(
                    model=self.llm,
                    tools=self.tools
                )
                logger.info("✅ Image subagent initialized with fallback configuration")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback initialization also failed: {fallback_error}")
                raise
    
    def _get_system_message(self) -> str:
        """Get system message for the image analysis agent"""
        return """You are an expert agricultural image analyst specializing in plant disease detection and crop health assessment.

**Your Core Responsibilities:**
🌱 Plant disease identification and diagnosis
🔬 Agricultural image analysis using AI models  
📊 Crop health assessment and recommendations
🎯 Accurate disease classification with confidence scores

**Available Tools:**
- plant_analysis_tool: Analyze plant images for disease detection using trained ML models
ALWAYS CALL THIS ABOVE TOOL. IF YOU ARE BEING ASKED TO ANSWER A QUESTION.
IT WILL AUTOMATICALLY USE THE IMAGE which was provided in the conversation by the user. You dont need to ask.

**Response Guidelines:**
✅ Always provide confidence scores with predictions
✅ Explain the disease in simple, farmer-friendly terms
✅ Include practical treatment recommendations
✅ Mention if the plant appears healthy
✅ Be honest about model limitations and uncertainty
❌ Never provide medical advice for human consumption
❌ Don't guarantee treatment outcomes
❌ Avoid overly technical jargon

Remember: You're helping farmers and gardeners protect their crops and improve yields through accurate disease detection."""

    def _extract_base64_from_query(self, query: str) -> Optional[str]:
        """Extract base64 image data from query"""
        try:
            # Look for base64 data in the query
            if "data:image" in query:
                # Extract from data URL format
                match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', query)
                if match:
                    return match.group(1)
            
            # Look for raw base64 (long string of base64 characters)
            base64_pattern = r'([A-Za-z0-9+/]{100,}={0,2})'
            match = re.search(base64_pattern, query)
            if match:
                return match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting base64: {e}")
            return None
    
    def _determine_model_from_query(self, query: str) -> str:
        """Determine which model to use based on query content"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['apple', 'apples']):
            return 'apple'
        elif any(word in query_lower for word in ['tomato', 'tomatoes']):
            return 'tomato' 
        elif any(word in query_lower for word in ['strawberry', 'strawberries']):
            return 'strawberry'
        else:
            return 'auto'  # Auto-select appropriate model
    
    def process_query(self, state: Annotated[dict, InjectedState]) -> str:
        """Process image analysis query"""
        messages = state["messages"]
    
        # Find the first HumanMessage
        first_human = next((m for m in messages if isinstance(m, HumanMessage)), None )       
        content = first_human.content if first_human else ""
        # Extract conversationID using regex
        match = re.match(r"CONVERSATIONID:(\d+)", content)
        if not match:
            return "No conversationID found in first HumanMessage"
        conversation_id = match.group(1)
        try:
            if conversation_id in IMGSTORE:
                # Extract base64 data
                base64_data = IMGSTORE[conversation_id]
                if base64_data:
                    # Determine model to use
                    model_name = "auto"
                    
                    # Create focused query for the agent
                    analysis_query = f"Please analyze this plant image for disease detection using the {model_name} model. Image data provided."
                    
                    # Use the tool directly for better control
                    try:
                        import json
                        
                        # Create JSON input for the single-parameter tool
                        tool_input = json.dumps({
                            "image_data": base64_data,
                            "model_name": model_name
                        })
                        
                        result = plant_analysis_tool.invoke(tool_input)
                        
                        return result
                    
                        # {
                        #     'success': True,
                        #     'response': result,
                        #     'summary': result,
                        #     'analysis_type': 'image_disease_detection',
                        #     'model_used': model_name
                        # }
                        
                    except Exception as e:
                        logger.error(f"Direct tool analysis failed: {e}")
                        # Fallback to agent execution
                        return self._execute_with_agent(analysis_query)
                else:
                    return 'I could not find valid image data in your message. Please ensure the image is properly encoded in base64 format.'
                    
        except Exception as e:
            logger.error(f"❌ Error in image agent processing: {e}")
            return f'I encountered an error while analyzing your image: {str(e)}'
    
    def _execute_with_agent(self, query: str) -> Dict[str, Any]:
        """Execute query using the conversational agent"""
        try:
            # For LangGraph agents, we need to invoke with different structure
            result = self.agent_executor.invoke({"messages": [("user", query)]})
            
            # Extract the final response
            if "messages" in result and result["messages"]:
                # Get the last message from the agent
                final_message = result["messages"][-1]
                if hasattr(final_message, 'content'):
                    response = final_message.content
                else:
                    response = str(final_message)
            else:
                response = str(result)
            
            return {
                'success': True,
                'response': response,
                'summary': response,
                'intermediate_steps': result.get('intermediate_steps', [])
            }
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': f'I encountered an error processing your request: {str(e)}'
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        return self.capabilities
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        status = {
            'agent_name': self.name,
            'llm_status': 'initialized' if self.llm else 'not_initialized',
            'agent_status': 'initialized' if self.agent_executor else 'not_initialized', 
            'memory_status': 'not_used',  # Memory not used with LangGraph
            'tools_count': len(self.tools),
            'available_models': self._check_available_models()
        }
        
        return {
            'status': 'healthy' if all(v != 'not_initialized' for v in status.values() if isinstance(v, str)) else 'unhealthy',
            'details': status
        }
    
    def _check_available_models(self) -> Dict[str, bool]:
        """Check which models are available"""
        from pathlib import Path
        
        models_dir = Path("models")
        model_files = {
            "apple": "Apple_Disease_Model_best.keras",
            "apple_final": "Apple_Disease_Model_final.keras",
            "plm_h5": "plm.h5", 
            "plm_keras": "plm.keras",
            "strawberry": "Strawberry_Disease_Model_best.keras",
            "tomato": "Tomato_Disease_Model_best.keras",
            "tomato_final": "Tomato_Disease_Model_final.keras"
        }
        
        availability = {}
        for model_name, filename in model_files.items():
            model_path = models_dir / filename
            availability[model_name] = model_path.exists()
            
        return availability

# Create instance for import
image_subagent = ImageSubAgent()
import json
tool_input = json.dumps({
                            "image_data": "data:image/jpeg;base64,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",
                            "model_name": "auto"
                        })
plant_analysis_tool(tool_input)