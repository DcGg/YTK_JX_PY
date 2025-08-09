"""安全认证模块

实现JWT token管理、密码加密、权限验证等核心安全功能。

Author: 云推客严选开发团队
Date: 2024
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict, List
from uuid import UUID

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from .config import get_settings
from ..models.user import User, UserRole

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()

# 获取配置
settings = get_settings()


class SecurityManager:
    """安全管理器
    
    负责处理密码加密、JWT token生成和验证、权限检查等安全相关功能。
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码
        
        Args:
            plain_password: 明文密码
            hashed_password: 哈希密码
            
        Returns:
            bool: 密码是否匹配
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希值
        
        Args:
            password: 明文密码
            
        Returns:
            str: 哈希密码
        """
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        subject: Union[str, Any], 
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建访问令牌
        
        Args:
            subject: 令牌主体（通常是用户ID）
            expires_delta: 过期时间增量
            additional_claims: 额外声明
            
        Returns:
            str: JWT访问令牌
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "access",
            "iat": datetime.utcnow()
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        encoded_jwt = jwt.encode(
            to_encode, 
            self.secret_key, 
            algorithm=self.algorithm
        )
        return encoded_jwt
    
    def create_refresh_token(
        self, 
        subject: Union[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌
        
        Args:
            subject: 令牌主体（通常是用户ID）
            expires_delta: 过期时间增量
            
        Returns:
            str: JWT刷新令牌
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=self.refresh_token_expire_days
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "refresh",
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32)  # JWT ID for refresh token
        }
        
        encoded_jwt = jwt.encode(
            to_encode, 
            self.secret_key, 
            algorithm=self.algorithm
        )
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """验证令牌
        
        Args:
            token: JWT令牌
            token_type: 令牌类型（access或refresh）
            
        Returns:
            Dict[str, Any]: 令牌载荷
            
        Raises:
            HTTPException: 令牌无效或过期
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # 检查令牌类型
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def generate_api_key(self) -> str:
        """生成API密钥
        
        Returns:
            str: API密钥
        """
        return secrets.token_urlsafe(32)
    
    def generate_verification_code(self, length: int = 6) -> str:
        """生成验证码
        
        Args:
            length: 验证码长度
            
        Returns:
            str: 验证码
        """
        import random
        import string
        
        return ''.join(random.choices(string.digits, k=length))
    
    def create_password_reset_token(self, email: str) -> str:
        """创建密码重置令牌
        
        Args:
            email: 用户邮箱
            
        Returns:
            str: 密码重置令牌
        """
        delta = timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        now = datetime.utcnow()
        expires = now + delta
        
        exp = expires.timestamp()
        encoded_jwt = jwt.encode(
            {"exp": exp, "nbf": now, "sub": email, "type": "password_reset"},
            self.secret_key,
            algorithm=self.algorithm,
        )
        return encoded_jwt
    
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """验证密码重置令牌
        
        Args:
            token: 密码重置令牌
            
        Returns:
            Optional[str]: 用户邮箱，如果令牌无效则返回None
        """
        try:
            decoded_token = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            if decoded_token.get("type") != "password_reset":
                return None
                
            return decoded_token["sub"]
        except jwt.JWTError:
            return None


# 全局安全管理器实例
security_manager = SecurityManager()


class PermissionChecker:
    """权限检查器
    
    用于检查用户权限和角色。
    """
    
    @staticmethod
    def check_user_role(user: User, required_roles: List[UserRole]) -> bool:
        """检查用户角色
        
        Args:
            user: 用户对象
            required_roles: 需要的角色列表
            
        Returns:
            bool: 是否有权限
        """
        return user.role in required_roles
    
    @staticmethod
    def check_user_active(user: User) -> bool:
        """检查用户是否激活
        
        Args:
            user: 用户对象
            
        Returns:
            bool: 用户是否激活
        """
        return user.is_active
    
    @staticmethod
    def check_resource_owner(user: User, resource_user_id: UUID) -> bool:
        """检查资源所有者
        
        Args:
            user: 当前用户
            resource_user_id: 资源所有者ID
            
        Returns:
            bool: 是否是资源所有者
        """
        return user.id == resource_user_id
    
    @staticmethod
    def check_merchant_access(user: User, merchant_id: UUID) -> bool:
        """检查商家访问权限
        
        Args:
            user: 当前用户
            merchant_id: 商家ID
            
        Returns:
            bool: 是否有访问权限
        """
        # 商家只能访问自己的资源
        if user.role == UserRole.MERCHANT:
            return user.id == merchant_id
        
        # 管理员可以访问所有资源
        return user.role == UserRole.ADMIN


# 权限检查器实例
permission_checker = PermissionChecker()


def get_current_user_from_token(token: str) -> Dict[str, Any]:
    """从令牌获取当前用户信息
    
    Args:
        token: JWT令牌
        
    Returns:
        Dict[str, Any]: 用户信息
        
    Raises:
        HTTPException: 令牌无效
    """
    try:
        payload = security_manager.verify_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """获取当前用户ID
    
    Args:
        credentials: HTTP认证凭据
        
    Returns:
        UUID: 用户ID
    """
    payload = get_current_user_from_token(credentials.credentials)
    user_id = payload.get("sub")
    
    try:
        return UUID(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(allowed_roles: List[UserRole]):
    """角色权限装饰器
    
    Args:
        allowed_roles: 允许的角色列表
        
    Returns:
        Callable: 装饰器函数
    """
    def role_checker(credentials: HTTPAuthorizationCredentials = Depends(security)):
        payload = get_current_user_from_token(credentials.credentials)
        user_role = payload.get("role")
        
        if not user_role or UserRole(user_role) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return payload
    
    return role_checker


def require_active_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """要求激活用户
    
    Args:
        credentials: HTTP认证凭据
        
    Returns:
        Dict[str, Any]: 用户信息
    """
    payload = get_current_user_from_token(credentials.credentials)
    is_active = payload.get("is_active", False)
    
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    
    return payload


def optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """可选用户认证
    
    Args:
        credentials: HTTP认证凭据（可选）
        
    Returns:
        Optional[Dict[str, Any]]: 用户信息，如果未认证则返回None
    """
    if not credentials:
        return None
    
    try:
        return get_current_user_from_token(credentials.credentials)
    except HTTPException:
        return None


class RateLimiter:
    """速率限制器
    
    用于API请求频率限制。
    """
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window: int = 3600
    ) -> bool:
        """检查是否允许请求
        
        Args:
            key: 限制键（通常是用户ID或IP）
            limit: 限制次数
            window: 时间窗口（秒）
            
        Returns:
            bool: 是否允许请求
        """
        now = datetime.utcnow().timestamp()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # 清理过期请求
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if now - req_time < window
        ]
        
        # 检查是否超过限制
        if len(self.requests[key]) >= limit:
            return False
        
        # 记录当前请求
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str, limit: int, window: int = 3600) -> int:
        """获取剩余请求次数
        
        Args:
            key: 限制键
            limit: 限制次数
            window: 时间窗口（秒）
            
        Returns:
            int: 剩余请求次数
        """
        now = datetime.utcnow().timestamp()
        
        if key not in self.requests:
            return limit
        
        # 清理过期请求
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if now - req_time < window
        ]
        
        return max(0, limit - len(self.requests[key]))


# 全局速率限制器实例
rate_limiter = RateLimiter()


def create_rate_limit_dependency(limit: int, window: int = 3600):
    """创建速率限制依赖
    
    Args:
        limit: 限制次数
        window: 时间窗口（秒）
        
    Returns:
        Callable: 依赖函数
    """
    def rate_limit_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        payload = get_current_user_from_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not rate_limiter.is_allowed(f"user:{user_id}", limit, window):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(
                        rate_limiter.get_remaining(f"user:{user_id}", limit, window)
                    ),
                    "X-RateLimit-Reset": str(int(datetime.utcnow().timestamp()) + window)
                }
            )
        
        return payload
    
    return rate_limit_checker


# 常用的权限依赖
require_merchant = require_roles([UserRole.MERCHANT])
require_leader = require_roles([UserRole.LEADER])
require_influencer = require_roles([UserRole.INFLUENCER])
require_any_user = require_roles([UserRole.MERCHANT, UserRole.LEADER, UserRole.INFLUENCER])

# 常用的速率限制
rate_limit_strict = create_rate_limit_dependency(100, 3600)  # 100次/小时
rate_limit_normal = create_rate_limit_dependency(1000, 3600)  # 1000次/小时
rate_limit_loose = create_rate_limit_dependency(10000, 3600)  # 10000次/小时