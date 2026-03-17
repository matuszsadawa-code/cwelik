"""
Authentication and Authorization Module

Implements JWT token generation and verification with role-based access control.
Supports three user roles: viewer, trader, admin.
Includes security event logging for authentication events.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from api.utils.security_logger import get_security_logger, SecurityEventType, SecurityEventSeverity

logger = logging.getLogger(__name__)
security_logger = get_security_logger()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer security scheme
security = HTTPBearer()


class UserRole:
    """User role definitions with permissions"""
    VIEWER = "viewer"    # Can view data (GET endpoints, WebSocket read-only)
    TRADER = "trader"    # Can view and execute trades (GET + POST for positions)
    ADMIN = "admin"      # Full access (all endpoints, configuration changes)


class User(BaseModel):
    """User model"""
    user_id: str
    username: str
    role: str
    disabled: bool = False


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: str
    username: str
    role: str


# In-memory user store (replace with database in production)
USERS_DB: Dict[str, Dict[str, Any]] = {
    "viewer_user": {
        "user_id": "user_001",
        "username": "viewer_user",
        "hashed_password": pwd_context.hash("viewer123"),
        "role": UserRole.VIEWER,
        "disabled": False
    },
    "trader_user": {
        "user_id": "user_002",
        "username": "trader_user",
        "hashed_password": pwd_context.hash("trader123"),
        "role": UserRole.TRADER,
        "disabled": False
    },
    "admin_user": {
        "user_id": "user_003",
        "username": "admin_user",
        "hashed_password": pwd_context.hash("admin123"),
        "role": UserRole.ADMIN,
        "disabled": False
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[User]:
    """
    Authenticate a user by username and password
    
    Args:
        username: Username
        password: Plain text password
        ip_address: IP address of the request
        user_agent: User agent string
        
    Returns:
        User object if authentication successful, None otherwise
    """
    user_data = USERS_DB.get(username)
    if not user_data:
        security_logger.log_auth_failure(
            username=username,
            ip_address=ip_address or "unknown",
            reason="User not found",
            user_agent=user_agent
        )
        return None
    
    if not verify_password(password, user_data["hashed_password"]):
        security_logger.log_auth_failure(
            username=username,
            ip_address=ip_address or "unknown",
            reason="Invalid password",
            user_agent=user_agent
        )
        return None
    
    user = User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data["role"],
        disabled=user_data.get("disabled", False)
    )
    
    # Log successful authentication
    security_logger.log_auth_success(
        user_id=user.user_id,
        username=user.username,
        ip_address=ip_address or "unknown",
        user_agent=user_agent
    )
    
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Token payload data (user_id, username, role)
        expires_delta: Token expiration time (default: 24 hours)
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and verify a JWT access token
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData object with user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        
        if user_id is None or username is None or role is None:
            raise credentials_exception
        
        token_data = TokenData(user_id=user_id, username=username, role=role)
        return token_data
    
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get current authenticated user from JWT token
    
    Dependency for protected endpoints
    
    Args:
        credentials: HTTP Bearer credentials from request header
        
    Returns:
        User object
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    # Get user from database
    user_data = USERS_DB.get(token_data.username)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data["role"],
        disabled=user_data.get("disabled", False)
    )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (not disabled)
    
    Dependency for protected endpoints
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


def require_role(required_role: str):
    """
    Role-based access control decorator
    
    Args:
        required_role: Required user role (viewer, trader, admin)
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(current_user: User = Depends(get_current_active_user), request: Request = None) -> User:
        # Admin has access to everything
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Trader has access to viewer and trader endpoints
        if required_role == UserRole.VIEWER and current_user.role in [UserRole.TRADER, UserRole.VIEWER]:
            return current_user
        
        # Check exact role match
        if current_user.role == required_role:
            return current_user
        
        # Log unauthorized access attempt
        ip_address = request.client.host if request else "unknown"
        user_agent = request.headers.get("user-agent") if request else None
        
        security_logger.log_unauthorized_access(
            user_id=current_user.user_id,
            username=current_user.username,
            ip_address=ip_address,
            resource=request.url.path if request else "unknown",
            required_role=required_role,
            user_role=current_user.role,
            user_agent=user_agent
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required role: {required_role}"
        )
    
    return role_checker


# Convenience dependencies for different access levels
require_viewer = require_role(UserRole.VIEWER)
require_trader = require_role(UserRole.TRADER)
require_admin = require_role(UserRole.ADMIN)


def verify_websocket_token(token: str) -> Optional[User]:
    """
    Verify WebSocket authentication token
    
    Args:
        token: JWT token from query params or headers
        
    Returns:
        User object if valid, None otherwise
    """
    try:
        token_data = decode_access_token(token)
        user_data = USERS_DB.get(token_data.username)
        
        if user_data is None or user_data.get("disabled", False):
            return None
        
        return User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            role=user_data["role"],
            disabled=user_data.get("disabled", False)
        )
    
    except HTTPException:
        return None
    except Exception as e:
        logger.error(f"WebSocket token verification error: {e}")
        return None
