# app/routers/auth_router.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.dependencies import get_user_mongodb_repository
from app.repositories.user_mongodb_repository import UserMongoDBRepository
from app.core.schema import UserCreate, UserLogin # Assuming we'll put these in a separate schemas file

router = APIRouter(
    prefix="/user",
    tags=["User"]
)

@router.post("/signup")
async def signup_endpoint(
    user_create: UserCreate,
    user_mongodb_repository: UserMongoDBRepository = Depends(get_user_mongodb_repository)
):
    if user_mongodb_repository.find_user_by_email(user_create.user_email):
        raise HTTPException(status_code=400, detail="User with this email already exists.")
    try:
        user=user_mongodb_repository.create_user(user_create)
        return {"message": "User registered successfully!", "user_id": str(user.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register user: {e}")




@router.post("/login")
async def login_endpoint(
    user_login: UserLogin,
    user_mongodb_repository: UserMongoDBRepository = Depends(get_user_mongodb_repository)
):
    try:
        user = user_mongodb_repository.authenticate_user(user_login)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        return {"message": "Login successful!", "user_id": str(user.id), "user_name": user.user_name}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error.")
