from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from datetime import datetime
import os
from motor.motor_asyncio import AsyncIOMotorClient
import google.generativeai as genai
from bson import ObjectId
import json

# Initialize FastAPI app
app = FastAPI(title="Farmer Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.farmer_agent

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "your-gemini-api-key"))
model = genai.GenerativeModel('gemini-pro')

# Pydantic models
class UserRegistration(BaseModel):
    email: str
    mobile: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    name: str
    age: int
    state: str
    district: str

class ChatMessage(BaseModel):
    message: str
    language: str
    userId: str
    conversationId: Optional[str] = None

class Message(BaseModel):
    id: str
    text: str
    isUser: bool
    timestamp: datetime

class Conversation(BaseModel):
    id: str
    userId: str
    title: str
    messages: List[Message]
    createdAt: datetime

# Helper function to convert ObjectId to string
def serialize_doc(doc):
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

# Authentication endpoints
@app.post("/api/auth/register")
async def register_user(user_data: UserRegistration):
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create new user
        user_doc = {
            "email": user_data.email,
            "mobile": user_data.mobile,
            "password": user_data.password,  # In production, hash this password
            "name": "",
            "age": None,
            "state": "",
            "district": "",
            "isOnboarded": False,
            "createdAt": datetime.utcnow()
        }
        
        result = await db.users.insert_one(user_doc)
        user_doc["id"] = str(result.inserted_id)
        del user_doc["_id"]
        del user_doc["password"]
        
        return user_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login_user(login_data: UserLogin):
    try:
        # Find user by email and password
        user = await db.users.find_one({
            "email": login_data.email,
            "password": login_data.password  # In production, verify hashed password
        })
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user["id"] = str(user["_id"])
        del user["_id"]
        del user["password"]
        
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/{user_id}/profile")
async def update_user_profile(user_id: str, profile_data: UserProfile):
    try:
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "name": profile_data.name,
                    "age": profile_data.age,
                    "state": profile_data.state,
                    "district": profile_data.district,
                    "isOnboarded": True
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoints
@app.post("/api/chat")
async def chat_with_ai(chat_data: ChatMessage):
    try:
        # Get user context
        user = await db.users.find_one({"_id": ObjectId(chat_data.userId)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create context for the AI
        context = f"""
        You are an AI assistant helping farmers with agricultural questions.
        User details:
        - Name: {user.get('name', 'Farmer')}
        - Location: {user.get('district', '')}, {user.get('state', '')}
        - Language: {chat_data.language}
        
        Please provide helpful, practical advice for farming questions.
        Respond in the language: {chat_data.language}
        
        User question: {chat_data.message}
        """
        
        # Generate response using Gemini
        try:
            response = model.generate_content(context)
            ai_response = response.text
        except Exception as ai_error:
            # Fallback responses if AI fails
            fallback_responses = {
                "en": "I understand your farming question. For the best advice, I recommend consulting with local agricultural experts who can provide specific guidance for your region.",
                "hi": "मैं आपके खेती के सवाल को समझता हूं। सबसे अच्छी सलाह के लिए, मैं स्थानीय कृषि विशेषज्ञों से सलाह लेने की सिफारिश करता हूं।",
                "kn": "ನಾನು ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಯನ್ನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. ಉತ್ತಮ ಸಲಹೆಗಾಗಿ, ಸ್ಥಳೀಯ ಕೃಷಿ ತಜ್ಞರೊಂದಿಗೆ ಸಮಾಲೋಚಿಸಲು ನಾನು ಶಿಫಾರಸು ಮಾಡುತ್ತೇನೆ.",
                "mr": "मला तुमचा शेतीचा प्रश्न समजला आहे. सर्वोत्तम सल्ल्यासाठी, मी स्थानिक कृषी तज्ञांशी सल्लामसलत करण्याची शिफारस करतो."
            }
            ai_response = fallback_responses.get(chat_data.language, fallback_responses["en"])
        
        # Save conversation to database
        conversation_id = chat_data.conversationId or str(ObjectId())
        
        # Create or update conversation
        conversation_doc = {
            "id": conversation_id,
            "userId": chat_data.userId,
            "title": chat_data.message[:50] + ("..." if len(chat_data.message) > 50 else ""),
            "messages": [
                {
                    "id": str(ObjectId()),
                    "text": chat_data.message,
                    "isUser": True,
                    "timestamp": datetime.utcnow()
                },
                {
                    "id": str(ObjectId()),
                    "text": ai_response,
                    "isUser": False,
                    "timestamp": datetime.utcnow()
                }
            ],
            "createdAt": datetime.utcnow()
        }
        
        # Upsert conversation
        await db.conversations.update_one(
            {"id": conversation_id},
            {"$set": conversation_doc},
            upsert=True
        )
        
        return {"response": ai_response, "conversationId": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{user_id}")
async def get_user_conversations(user_id: str):
    try:
        conversations = await db.conversations.find(
            {"userId": user_id}
        ).sort("createdAt", -1).to_list(length=50)
        
        return [serialize_doc(conv) for conv in conversations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    try:
        conversation = await db.conversations.find_one({"id": conversation_id})
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation.get("messages", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
