from fastapi import APIRouter, HTTPException, status
from app.models import ChatMessage, ChatResponse, Conversation
from app.database import get_database
from app.services.ai_service import AIService
from bson import ObjectId
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_data: ChatMessage):
    """Handle chat message and get AI response"""
    db = get_database()
    
    try:
        # Get user data
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
        
        # Get AI response
        ai_response = await AIService.get_ai_response(
            chat_data.message,
            user,
            chat_data.language
        )
        
        # Generate conversation ID if not provided
        conversation_id = chat_data.conversationId or str(uuid.uuid4())
        
        # Create messages
        user_message = {
            "id": str(uuid.uuid4()),
            "text": chat_data.message,
            "isUser": True,
            "timestamp": datetime.utcnow()
        }
        
        ai_message = {
            "id": str(uuid.uuid4()),
            "text": ai_response,
            "isUser": False,
            "timestamp": datetime.utcnow()
        }
        
        # Check if conversation exists
        existing_conversation = await db.conversations.find_one({"id": conversation_id})
        
        if existing_conversation:
            # Update existing conversation
            await db.conversations.update_one(
                {"id": conversation_id},
                {
                    "$push": {
                        "messages": {"$each": [user_message, ai_message]}
                    }
                }
            )
        else:
            # Create new conversation
            conversation_doc = {
                "id": conversation_id,
                "userId": chat_data.userId,
                "title": chat_data.message[:50] + ("..." if len(chat_data.message) > 50 else ""),
                "messages": [user_message, ai_message],
                "createdAt": datetime.utcnow()
            }
            
            await db.conversations.insert_one(conversation_doc)
        
        return ChatResponse(response=ai_response, conversationId=conversation_id)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )

@router.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str):
    """Get all conversations for a user"""
    db = get_database()
    
    try:
        # Validate user ID
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Get conversations
        conversations = await db.conversations.find(
            {"userId": user_id}
        ).sort("createdAt", -1).limit(50).to_list(length=50)
        
        # Format response
        formatted_conversations = []
        for conv in conversations:
            formatted_conv = {
                "id": conv["id"],
                "userId": conv["userId"],
                "title": conv["title"],
                "messages": conv["messages"],
                "createdAt": conv["createdAt"]
            }
            formatted_conversations.append(formatted_conv)
        
        return formatted_conversations
        
    except HTTPException:
        raise
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
        # Find conversation
        conversation = await db.conversations.find_one({"id": conversation_id})
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return conversation.get("messages", [])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}"
        )
