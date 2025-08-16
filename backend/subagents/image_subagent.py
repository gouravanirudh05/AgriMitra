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
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
# Import the image tools
from tools.image_tool import plant_analysis_tool, plant_models_tool, analyze_plant_image

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageSubAgent:
    """Subagent specialized in plant disease detection and image analysis"""
    
    def __init__(self):
        self.name = "Image Analysis Agent"
        self.description = "Specialized agent for plant disease detection, crop analysis, and agricultural image diagnosis"
        self.llm = None
        self.agent_executor = None
        self.memory = None
        self.tools = [plant_analysis_tool, plant_models_tool]
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
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            
            # Initialize agent with only the required parameters
            self.agent_executor = create_react_agent(
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
- plant_models_tool: Get information about available disease detection models

**Key Capabilities:**
- Support for multiple crop types (apple, tomato, strawberry, general crops)
- Disease detection with confidence scores
- Top-3 prediction rankings
- Treatment recommendations
- Model selection guidance

**Analysis Protocol:**
1. **Image Processing**: Extract and process base64 image data
2. **Model Selection**: Choose appropriate model based on crop type or use auto-detection
3. **Disease Analysis**: Run inference and get predictions
4. **Results Interpretation**: Provide clear, actionable diagnosis
5. **Recommendations**: Offer treatment and management advice

**Response Guidelines:**
✅ Always provide confidence scores with predictions
✅ Explain the disease in simple, farmer-friendly terms
✅ Include practical treatment recommendations
✅ Mention if the plant appears healthy
✅ Be honest about model limitations and uncertainty
❌ Never provide medical advice for human consumption
❌ Don't guarantee treatment outcomes
❌ Avoid overly technical jargon

**Image Data Handling:**
- Accept base64 encoded images (with or without data URL prefix)
- Support JPG, PNG, JPEG formats
- Process images automatically and save for analysis
- Handle various image qualities and lighting conditions

**When analyzing images:**
1. First check if image data is present in the query
2. Extract the base64 data properly
3. Use plant_analysis_tool with appropriate model
4. Interpret results in agricultural context
5. Provide actionable recommendations

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
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process image analysis query"""
        try:
            logger.info(f"🔍 Image agent processing: {query[:100]}...")
            
            # Check if this is an image analysis request
            has_image_data = "data:image" in query or len(re.findall(r'[A-Za-z0-9+/=]{50,}', query)) > 0
            
            if has_image_data:
                # Extract base64 data
                base64_data = self._extract_base64_from_query(query)
                if base64_data:
                    # Determine model to use
                    model_name = self._determine_model_from_query(query)
                    
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
                        
                        return {
                            'success': True,
                            'response': result,
                            'summary': result,
                            'analysis_type': 'image_disease_detection',
                            'model_used': model_name
                        }
                        
                    except Exception as e:
                        logger.error(f"Direct tool analysis failed: {e}")
                        # Fallback to agent execution
                        return self._execute_with_agent(analysis_query)
                else:
                    return {
                        'success': False,
                        'error': 'Could not extract image data from the query',
                        'response': 'I could not find valid image data in your message. Please ensure the image is properly encoded in base64 format.'
                    }
            
            # Handle non-image queries (model info, general questions)
            elif any(word in query.lower() for word in ['model', 'available', 'list', 'what can', 'help']):
                # Use plant_models_tool for model information
                try:
                    result = plant_models_tool.invoke("")
                    return {
                        'success': True,
                        'response': result,
                        'summary': result,
                        'analysis_type': 'model_information'
                    }
                except Exception as e:
                    logger.error(f"Model info tool failed: {e}")
                    return self._execute_with_agent(query)
            
            else:
                # General image-related query, use agent
                return self._execute_with_agent(query)
                
        except Exception as e:
            logger.error(f"❌ Error in image agent processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': f'I encountered an error while analyzing your image: {str(e)}'
            }
    
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