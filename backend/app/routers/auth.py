from fastapi import APIRouter, HTTPException, status
from app.models import UserRegistration, UserLogin, UserResponse, ErrorResponse
from app.database import get_database
from datetime import datetime
import hashlib
import secrets

router = APIRouter()

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        salt, hash_value = hashed_password.split(":")
        return hashlib.sha256((password + salt).encode()).hexdigest() == hash_value
    except:
        return False

@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserRegistration):
    """Register a new user"""
    db = get_database()
    
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create new user document
        user_doc = {
            "email": user_data.email,
            "mobile": user_data.mobile,
            "password": hash_password(user_data.password),
            "name": "",
            "age": None,
            "state": "",
            "district": "",
            "isOnboarded": False,
            "createdAt": datetime.utcnow()
        }
        
        # Insert user into database
        result = await db.users.insert_one(user_doc)
        
        # Prepare response (exclude password)
        user_response = {
            "id": str(result.inserted_id),
            "email": user_data.email,
            "mobile": user_data.mobile,
            "name": "",
            "age": None,
            "state": "",
            "district": "",
            "isOnboarded": False,
            "createdAt": user_doc["createdAt"]
        }
        
        return UserResponse(**user_response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=UserResponse)
async def login_user(login_data: UserLogin):
    """Login user"""
    db = get_database()
    
    try:
        # Find user by email
        user = await db.users.find_one({"email": login_data.email})
        
        if not user or not verify_password(login_data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Prepare response (exclude password)
        user_response = {
            "id": str(user["_id"]),
            "email": user["email"],
            "mobile": user.get("mobile", ""),
            "name": user.get("name", ""),
            "age": user.get("age"),
            "state": user.get("state", ""),
            "district": user.get("district", ""),
            "isOnboarded": user.get("isOnboarded", False),
            "createdAt": user["createdAt"]
        }
        
        return UserResponse(**user_response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )
