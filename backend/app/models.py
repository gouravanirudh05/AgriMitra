from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User models
class UserRegistration(BaseModel):
    email: EmailStr
    mobile: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    name: str
    age: int
    state: str
    district: str

class UserResponse(BaseModel):
    id: str
    email: str
    mobile: Optional[str] = None
    name: Optional[str] = ""
    age: Optional[int] = None
    state: Optional[str] = ""
    district: Optional[str] = ""
    isOnboarded: bool = False
    createdAt: datetime

# Chat models
class ChatMessage(BaseModel):
    message: str
    youtube: Optional[str] = None
    sources: Optional[str] = None
    image: Optional[str] = None
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

class ChatResponse(BaseModel):
    response: str
    conversationId: str

# Response models
class SuccessResponse(BaseModel):
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    error: str
    success: bool = False
