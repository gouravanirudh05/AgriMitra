from fastapi import APIRouter, HTTPException, status
from app.models import UserProfile, SuccessResponse
from app.database import get_database
from bson import ObjectId

router = APIRouter()

@router.put("/{user_id}/profile", response_model=SuccessResponse)
async def update_user_profile(user_id: str, profile_data: UserProfile):
    """Update user profile information"""
    db = get_database()
    
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Update user profile
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return SuccessResponse(message="Profile updated successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )

@router.get("/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile information"""
    db = get_database()
    
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Find user
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
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
        
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )
