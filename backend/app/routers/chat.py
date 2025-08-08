# app/routers/chat.py
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.models import ChatMessage, ChatResponse
from datetime import datetime, timedelta
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

# Import the enhanced orchestrator
from agent.orchestrator import get_orchestrator, AgentOrchestrator

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory conversation store for demo (consider using Redis/DB in production)
FAKE_DB = {"conversations": {}}

# Global orchestrator instance
orchestrator_instance: Optional[AgentOrchestrator] = None


class ConversationManager:
    """Manages conversation state and history"""
    
    @staticmethod
    def get_or_create_conversation(user_id: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Get existing conversation or create a new one"""
        if conversation_id and conversation_id in FAKE_DB["conversations"]:
            conv = FAKE_DB["conversations"][conversation_id]
            # Verify user ownership
            if conv["userId"] != user_id:
                raise HTTPException(status_code=403, detail="Access denied to conversation")
            return conv
        else:
            # Create new conversation
            conv_id = str(uuid.uuid4())
            conv = {
                "id": conv_id,
                "userId": user_id,
                "messages": [],
                "createdAt": datetime.utcnow(),
                "lastActivity": datetime.utcnow(),
                "metadata": {}
            }
            FAKE_DB["conversations"][conv_id] = conv
            return conv
    
    @staticmethod
    def add_message(conversation: Dict[str, Any], text: str, is_user: bool, metadata: Optional[Dict] = None) -> str:
        """Add a message to the conversation"""
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "text": text,
            "isUser": is_user,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }
        conversation["messages"].append(message)
        conversation["lastActivity"] = datetime.utcnow()
        return message_id
    
    @staticmethod
    def get_recent_context(conversation: Dict[str, Any], max_messages: int = 10) -> str:
        """Get recent conversation context for the agent"""
        recent_messages = conversation["messages"][-max_messages:]
        context = []
        
        for msg in recent_messages:
            role = "User" if msg["isUser"] else "Assistant"
            context.append(f"{role}: {msg['text']}")
        
        return "\n".join(context) if context else ""
    
    @staticmethod
    def cleanup_old_conversations(max_age_hours: int = 24):
        """Background task to clean up old conversations"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            conversations_to_remove = []
            for conv_id, conv in FAKE_DB["conversations"].items():
                if conv["lastActivity"] < cutoff_time:
                    conversations_to_remove.append(conv_id)
            
            for conv_id in conversations_to_remove:
                del FAKE_DB["conversations"][conv_id]
            
            logger.info(f"Cleaned up {len(conversations_to_remove)} old conversations")
        except Exception as e:
            logger.error(f"Error during conversation cleanup: {e}")


async def get_orchestrator_instance() -> AgentOrchestrator:
    """Get the global orchestrator instance"""
    global orchestrator_instance
    if orchestrator_instance is None:
        orchestrator_instance = await get_orchestrator()
    return orchestrator_instance


@router.on_event("startup")
async def startup_event():
    """Initialize the orchestrator when the router starts"""
    try:
        logger.info("🚀 Initializing chat router...")
        
        # Initialize orchestrator
        global orchestrator_instance
        orchestrator_instance = await get_orchestrator()
        
        # Verify orchestrator health
        health = orchestrator_instance.health_check()
        logger.info(f"Orchestrator health: {health['status']}")
        
        if health['status']['orchestrator'] != 'healthy':
            raise RuntimeError(f"Orchestrator unhealthy: {health['status']}")
        
        logger.info("✅ Chat router initialized successfully")
        logger.info(f"Available tools: {[t.name for t in orchestrator_instance.tools]}")
        
    except Exception as e:
        logger.error(f"❌ Chat router initialization failed: {e}")
        # Don't raise - allow server to start but log the error
        orchestrator_instance = None


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup when router shuts down"""
    logger.info("🔄 Chat router shutting down...")
    # Add any cleanup logic here if needed


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatMessage, request: Request, background_tasks: BackgroundTasks):
    """Main chat endpoint with orchestrator integration"""
    
    # Validate input
    if not payload.userId or not payload.message:
        raise HTTPException(status_code=400, detail="Missing userId or message")
    
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Get orchestrator
    try:
        orchestrator = await get_orchestrator_instance()
        if orchestrator is None:
            raise HTTPException(status_code=503, detail="Agent service unavailable")
    except Exception as e:
        logger.error(f"Failed to get orchestrator: {e}")
        raise HTTPException(status_code=503, detail=f"Agent service error: {e}")
    
    # Get or create conversation
    try:
        conversation = ConversationManager.get_or_create_conversation(
            payload.userId, 
            payload.conversationId
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Conversation management error: {e}")
        raise HTTPException(status_code=500, detail="Conversation management error")
    
    # Add user message
    user_message_id = ConversationManager.add_message(
        conversation, 
        payload.message, 
        is_user=True,
        metadata={"source": "chat_endpoint"}
    )
    
    logger.info(f"Processing message for user {payload.userId}: {payload.message[:100]}...")
    
    # Prepare context for the agent
    recent_context = ConversationManager.get_recent_context(conversation, max_messages=8)
    
    # Enhanced query with context
    enhanced_query = payload.message
    if recent_context and len(conversation["messages"]) > 1:
        # Only add context if there's previous conversation
        enhanced_query = f"Context from recent conversation:\n{recent_context}\n\nCurrent question: {payload.message}"
    
    # Call orchestrator
    start_time = datetime.utcnow()
    try:
        result = await orchestrator.query(
            enhanced_query,
            conversation_id=conversation["id"],
            user_id=payload.userId
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        if not result['success']:
            logger.error(f"Orchestrator query failed: {result['error']}")
            # Add error message to conversation
            fallback_response = "I apologize, but I encountered an error processing your request. Please try again or rephrase your question."
            ConversationManager.add_message(
                conversation,
                fallback_response,
                is_user=False,
                metadata={"error": result['error'], "processing_time": processing_time}
            )
            
            # Return response instead of raising exception to avoid 500 error
            return ChatResponse(
                response=fallback_response,
                conversationId=conversation["id"]
            )
        
        response_text = result['response']
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"Unexpected error during query processing: {e}")
        
        # Add fallback message
        fallback_response = "I'm sorry, I encountered an unexpected error. Please try again later."
        ConversationManager.add_message(
            conversation,
            fallback_response,
            is_user=False,
            metadata={"error": str(e), "processing_time": processing_time, "fallback": True}
        )
        
        # Return response instead of raising exception to avoid 500 error
        return ChatResponse(
            response=fallback_response,
            conversationId=conversation["id"]
        )
    
    # Add AI response to conversation
    ai_message_id = ConversationManager.add_message(
        conversation,
        response_text,
        is_user=False,
        metadata={
            "processing_time": processing_time,
            "tools_used": result.get('tools_used', []),
            "model_used": orchestrator.config.get('model', 'unknown') if hasattr(orchestrator, 'config') else 'unknown'
        }
    )
    
    # Schedule background cleanup with error handling
    try:
        background_tasks.add_task(ConversationManager.cleanup_old_conversations)
    except Exception as e:
        logger.error(f"Failed to schedule cleanup task: {e}")
        # Don't fail the request if cleanup scheduling fails
    
    logger.info(f"✅ Response generated in {processing_time:.2f}s for user {payload.userId}")
    
    return ChatResponse(
        response=response_text,
        conversationId=conversation["id"]
    )


@router.post("/chat/stream")
async def chat_stream_endpoint(payload: ChatMessage, request: Request):
    """Streaming chat endpoint (for future implementation)"""
    # Placeholder for streaming implementation
    raise HTTPException(status_code=501, detail="Streaming not implemented yet")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user_id: str):
    """Get conversation history"""
    if conversation_id not in FAKE_DB["conversations"]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = FAKE_DB["conversations"][conversation_id]
    
    if conversation["userId"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": conversation["id"],
        "userId": conversation["userId"],
        "messages": conversation["messages"],
        "createdAt": conversation["createdAt"],
        "lastActivity": conversation["lastActivity"],
        "messageCount": len(conversation["messages"])
    }


@router.get("/conversations")
async def list_conversations(user_id: str, limit: int = 10, offset: int = 0):
    """List user's conversations"""
    user_conversations = [
        {
            "id": conv["id"],
            "createdAt": conv["createdAt"],
            "lastActivity": conv["lastActivity"],
            "messageCount": len(conv["messages"]),
            "preview": conv["messages"][-1]["text"][:100] + "..." if conv["messages"] else ""
        }
        for conv in FAKE_DB["conversations"].values()
        if conv["userId"] == user_id
    ]
    
    # Sort by last activity (newest first)
    user_conversations.sort(key=lambda x: x["lastActivity"], reverse=True)
    
    # Apply pagination
    paginated = user_conversations[offset:offset + limit]
    
    return {
        "conversations": paginated,
        "total": len(user_conversations),
        "limit": limit,
        "offset": offset
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str):
    """Delete a conversation"""
    if conversation_id not in FAKE_DB["conversations"]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = FAKE_DB["conversations"][conversation_id]
    
    if conversation["userId"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    del FAKE_DB["conversations"][conversation_id]
    
    return {"message": "Conversation deleted successfully"}


@router.get("/health")
async def chat_health_check():
    """Health check endpoint for chat service"""
    try:
        orchestrator = await get_orchestrator_instance()
        orchestrator_health = orchestrator.health_check() if orchestrator else {"status": {"orchestrator": "not_available"}}
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "conversations_count": len(FAKE_DB["conversations"]),
            "orchestrator": orchestrator_health["status"],
            "tools_available": len(orchestrator.tools) if orchestrator else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/tools")
async def list_available_tools():
    """List available tools and their descriptions"""
    try:
        orchestrator = await get_orchestrator_instance()
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        
        return orchestrator.get_tool_info()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tools: {e}")


@router.post("/debug/query")
async def debug_query(payload: dict):
    """Debug endpoint for testing queries directly"""
    try:
        orchestrator = await get_orchestrator_instance()
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not available")
        
        message = payload.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Message required")
        
        result = await orchestrator.query(message)
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    