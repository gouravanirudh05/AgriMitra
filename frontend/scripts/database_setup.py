from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from datetime import datetime
import os

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

async def setup_database():
    """Setup MongoDB database with required collections and indexes"""
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.farmer_agent
    
    try:
        # Create users collection with indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("mobile")
        await db.users.create_index("createdAt")
        
        # Create conversations collection with indexes
        await db.conversations.create_index("id", unique=True)
        await db.conversations.create_index("userId")
        await db.conversations.create_index("createdAt")
        
        # Create sample data for testing
        sample_user = {
            "email": "farmer@example.com",
            "mobile": "+919876543210",
            "password": "password123",  # In production, this should be hashed
            "name": "Ravi Kumar",
            "age": 35,
            "state": "Karnataka",
            "district": "Bangalore Rural",
            "isOnboarded": True,
            "createdAt": datetime.utcnow()
        }
        
        # Insert sample user if not exists
        existing_user = await db.users.find_one({"email": sample_user["email"]})
        if not existing_user:
            await db.users.insert_one(sample_user)
            print("Sample user created successfully")
        
        print("Database setup completed successfully!")
        print("Collections created:")
        print("- users (with email, mobile, createdAt indexes)")
        print("- conversations (with id, userId, createdAt indexes)")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(setup_database())
