from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from datetime import datetime

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "farmer_agent"

client = None
db = None

async def init_db():
    """Initialize database connection and create indexes"""
    global client, db
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    # Create indexes
    await create_indexes()
    print("Database initialized successfully")

async def create_indexes():
    """Create database indexes for better performance"""
    # Users collection indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mobile")
    await db.users.create_index("createdAt")
    
    # Conversations collection indexes
    await db.conversations.create_index("id", unique=True)
    await db.conversations.create_index("userId")
    await db.conversations.create_index("createdAt")
    
    print("Database indexes created successfully")

def get_database():
    """Get database instance"""
    return db

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    return None

def serialize_docs(docs):
    """Convert list of MongoDB documents to JSON serializable format"""
    return [serialize_doc(doc) for doc in docs]
