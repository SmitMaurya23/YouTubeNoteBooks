# app/routers/auth_router.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.dependencies import get_mongodb_repository
from app.repositories.mongodb_repository import MongoDBRepository
from app.core.schema import UserCreate, UserLogin # Assuming we'll put these in a separate schemas file

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/signup")
async def signup_endpoint(
    user_data: UserCreate,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    try:
        user_id = await mongo_repo.create_user(user_data)
        return {"message": "User registered successfully!", "user_id": str(user_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register user: {e}")

@router.post("/login")
async def login_endpoint(
    user_data: UserLogin,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    try:
        user = await mongo_repo.authenticate_user(user_data)
       # return {"message": "Login successful!", "user_id": str(user.user_id), "user_name": user.user_name}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log in: {e}")