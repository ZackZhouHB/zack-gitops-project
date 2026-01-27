"""JWT Authentication - Simple local implementation
In production, replace with AWS Cognito or Auth0
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Local secret - in production use AWS Secrets Manager
SECRET_KEY = "dev-secret-change-in-production"
ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)

class User(BaseModel):
    user_id: str
    email: str
    groups: List[str]  # For access control: ["engineering", "hr", "admin"]
    
class TokenData(BaseModel):
    user_id: str
    email: str
    groups: List[str]
    exp: datetime

# Mock users for local dev
MOCK_USERS = {
    "admin": User(user_id="admin", email="admin@example.com", groups=["admin", "engineering", "hr"]),
    "engineer": User(user_id="engineer", email="eng@example.com", groups=["engineering"]),
    "hr_user": User(user_id="hr_user", email="hr@example.com", groups=["hr"]),
    "guest": User(user_id="guest", email="guest@example.com", groups=[]),
}

def create_token(user: User, expires_hours: int = 24) -> str:
    """Create JWT token for user"""
    payload = {
        "user_id": user.user_id,
        "email": user.email,
        "groups": user.groups,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Optional[User]:
    """Get current user from JWT token - returns None if no auth"""
    if not credentials:
        return None
    
    token_data = decode_token(credentials.credentials)
    return User(
        user_id=token_data.user_id,
        email=token_data.email,
        groups=token_data.groups
    )

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """Require authentication - raises 401 if not authenticated"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token_data = decode_token(credentials.credentials)
    return User(
        user_id=token_data.user_id,
        email=token_data.email,
        groups=token_data.groups
    )

def require_groups(required_groups: List[str]):
    """Decorator to require specific groups"""
    async def check_groups(user: User = Depends(require_auth)) -> User:
        if "admin" in user.groups:
            return user  # Admin bypasses
        if not any(g in user.groups for g in required_groups):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_groups
