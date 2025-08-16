# app/routers/chat.py - FIXED VERSION
from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.models import ChatMessage, ChatResponse
from app.database import get_database
from bson import ObjectId
from datetime import datetime, timedelta
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from subagents.youtube_agent_summary import YouTubeAgentLink, get_YouTubeAgentLink
from googletrans import Translator

translator = Translator()

# Import the enhanced orchestrator
from agent.orchestrator import get_orchestrator, AgentOrchestrator

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Global orchestrator instance
orchestrator_instance: Optional[AgentOrchestrator] = None


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

        global youtube_agent_link
        youtube_agent_link = get_YouTubeAgentLink()
        
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


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_data: ChatMessage):
    """Handle user query and return AI response using Orchestrator + Database"""
    db = get_database()

    try:
        # Validate user (KEEPING ORIGINAL VALIDATION)
        if not ObjectId.is_valid(chat_data.userId):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

        user = await db.users.find_one({"_id": ObjectId(chat_data.userId)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        USER_CONTEXT = {"state": user['state'] or "", "district": user['district'] or "", "name": user['name'] or ""}
        print(USER_CONTEXT)
        # Get orchestrator (NEW)
        try:
            orchestrator = await get_orchestrator_instance()
            if orchestrator is None:
                raise HTTPException(status_code=503, detail="Agent service unavailable")
        except Exception as e:
            logger.error(f"Failed to get orchestrator: {e}")
            raise HTTPException(status_code=503, detail=f"Agent service error: {e}")

        # Get conversation context for orchestrator
        conversation_id = chat_data.conversationId or str(uuid.uuid4())
        recent_context = ""
        
        if chat_data.conversationId:
            # Get recent messages from database for context
            existing_conv = await db.conversations.find_one({"id": conversation_id})
            if existing_conv and existing_conv.get("messages"):
                recent_messages = existing_conv["messages"][-8:]  # Last 8 messages
                context_parts = []
                for msg in recent_messages:
                    role = "User" if msg["isUser"] else "Assistant"
                    context_parts.append(f"{role}: {msg['text']}")
                recent_context = "\n".join(context_parts)
                
        lang_code = (await translator.detect(chat_data.message)).lang or "en"

        if lang_code != "en":
            translated_input = (await translator.translate(chat_data.message, src=lang_code, dest="en")).text
        else:
            translated_input = chat_data.message
        
        # Prepare enhanced query with context
        enhanced_query = translated_input
        if recent_context:
            enhanced_query = f"Context from recent conversation:\n{recent_context}\n\nCurrent question: {translated_input}"
        
        # Get response from Orchestrator (CHANGED FROM AIService)
        start_time = datetime.utcnow()
        try:
            result = await orchestrator.query(
                enhanced_query,
                conversation_id=conversation_id,
                user_id=chat_data.userId,
                user_context=USER_CONTEXT
                image=chat_data.image,
                user_id=chat_data.userId
            )
            print(chat_data.image)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            if not result['success']:
                logger.error(f"Orchestrator query failed: {result['error']}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"AI service error: {result['error']}"
                )
            
            ai_response = result['response']
            if lang_code != "en":
                final_response = (await translator.translate(ai_response, src="en", dest=lang_code)).text
            else:
                final_response = ai_response
            yt_link = []
            try:
                yt_link.append(youtube_agent_link.get_youtube_video(enhanced_query, ai_response))
            except Exception as e:
                logger.error(f"Error getting YouTube video link: {e}")
        except HTTPException:
            raise
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Unexpected error during query processing: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Chat failed: {str(e)}"
            )

        # Format messages (KEEPING ORIGINAL FORMAT)
        user_msg = {
            "id": str(uuid.uuid4()),
            "text": chat_data.message,
            "isUser": True,
            "timestamp": datetime.utcnow()
        }

        ai_msg = {
            "id": str(uuid.uuid4()),
            "text": final_response,
            "isUser": False,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "processing_time": processing_time,
                "tools_used": result.get('tools_used', []),
                "lang_code": lang_code,
                "actual_response": ai_response
            }
        }

        # Save to conversation (KEEPING ORIGINAL DATABASE LOGIC)
        existing = await db.conversations.find_one({"id": conversation_id})
        if existing:
            await db.conversations.update_one(
                {"id": conversation_id},
                {"$push": {"messages": {"$each": [user_msg, ai_msg]}}}
            )
        else:
            conv_doc = {
                "id": conversation_id,
                "userId": chat_data.userId,
                "title": chat_data.message[:50] + ("..." if len(chat_data.message) > 50 else ""),
                "messages": [user_msg, ai_msg],
                "createdAt": datetime.utcnow()
            }
            await db.conversations.insert_one(conv_doc)

        return ChatResponse(response=final_response, conversationId=conversation_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


# KEEPING ORIGINAL DATABASE-BASED ENDPOINTS
@router.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str):
    """Get all conversations for a user"""
    db = get_database()

    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

        conversations = await db.conversations.find(
            {"userId": user_id}
        ).sort("createdAt", -1).limit(50).to_list(length=50)

        return [
            {
                "id": c["id"],
                "userId": c["userId"],
                "title": c["title"],
                "messages": c["messages"],
                "createdAt": c["createdAt"]
            } for c in conversations
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get messages for a specific conversation"""
    db = get_database()

    try:
        conversation = await db.conversations.find_one({"id": conversation_id})
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return conversation.get("messages", [])

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}"
        )


# NEW ENDPOINTS FOR DEBUGGING/MONITORING
@router.get("/health")
async def chat_health_check():
    """Health check endpoint for chat service"""
    try:
        db = get_database()
        orchestrator = await get_orchestrator_instance()
        orchestrator_health = orchestrator.health_check() if orchestrator else {"status": {"orchestrator": "not_available"}}
        
        # Test database connection
        try:
            await db.conversations.count_documents({}, limit=1)
            db_status = "healthy"
        except:
            db_status = "unhealthy"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
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