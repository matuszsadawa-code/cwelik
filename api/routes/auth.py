"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from datetime import timedelta
import logging

from api.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    User,
    ACCESS_TOKEN_EXPIRE_HOURS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str
    user_id: str
    username: str
    role: str
    expires_in: int  # seconds


class UserInfoResponse(BaseModel):
    """User information response"""
    user_id: str
    username: str
    role: str
    disabled: bool


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT access token
    
    Args:
        request: Login credentials (username, password)
        
    Returns:
        LoginResponse with access token and user information
        
    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(request.username, request.password)
    
    if not user:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.disabled:
        logger.warning(f"Login attempt for disabled user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create access token
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in successfully: {user.username} (role: {user.role})")
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600  # Convert hours to seconds
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information
    
    Requires valid JWT token in Authorization header
    
    Returns:
        UserInfoResponse with user details
    """
    return UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role,
        disabled=current_user.disabled
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint (client-side token removal)
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint is provided for logging purposes.
    
    Returns:
        Success message
    """
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Logged out successfully"}
