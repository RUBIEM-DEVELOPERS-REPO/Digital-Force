"""Digital Force — Auth API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from database import get_db, User
from auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = ""
    role: str = "operator"

@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Username already exists")
    user = User(
        id=str(uuid.uuid4()), username=body.username, email=body.email,
        full_name=body.full_name, hashed_password=hash_password(body.password), role=body.role,
    )
    db.add(user)
    await db.flush()
    token = create_access_token({"sub": user.id, "username": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role}}

@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    user.last_login = datetime.utcnow()
    token = create_access_token({"sub": user.id, "username": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role, "full_name": user.full_name}}

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
