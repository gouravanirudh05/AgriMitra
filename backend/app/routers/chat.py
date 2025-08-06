from fastapi import APIRouter, HTTPException, status
from app.models import ChatMessage, ChatResponse
from app.database import get_database
from app.services.ai_service import AIService
from bson import ObjectId
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_data: ChatMessage):
    """Handle user query and return AI response using Gemini + FAISS"""
    db = get_database()

    try:
        # Validate user
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

        # Get response from AIService
        ai_response = await AIService.get_ai_response(
            chat_data.message,
            user,
            chat_data.language
        )

        # Conversation ID
        conversation_id = chat_data.conversationId or str(uuid.uuid4())

        # Format messages
        user_msg = {
            "id": str(uuid.uuid4()),
            "text": chat_data.message,
            "isUser": True,
            "timestamp": datetime.utcnow()
        }

        ai_msg = {
            "id": str(uuid.uuid4()),
            "text": ai_response,
            "isUser": False,
            "timestamp": datetime.utcnow()
        }

        # Save to conversation
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
