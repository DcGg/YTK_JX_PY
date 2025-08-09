"""用户认证API

提供用户注册、登录、token管理等认证相关接口。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import HTTPBearer
from loguru import logger

from ..core.security import get_current_user_id, require_active_user
from ..models.user import (
    User, UserCreate, UserUpdate, UserLogin, UserLoginResponse
)
from ..models.common import ResponseModel
from ..services.auth_service import get_auth_service, AuthService

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=ResponseModel[User])
async def register(
    user_data: UserCreate,
    wechat_code: Optional[str] = Body(None, description="微信登录code"),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[User]:
    """用户注册
    
    支持普通注册和微信注册。
    
    Args:
        user_data: 用户注册数据
        wechat_code: 微信登录code（可选）
        auth_service: 认证服务
        
    Returns:
        ResponseModel[User]: 注册结果
        
    Raises:
        HTTPException: 注册失败时抛出异常
    """
    try:
        result = await auth_service.register_user(user_data, wechat_code)
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册API异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=ResponseModel[UserLoginResponse])
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[UserLoginResponse]:
    """密码登录
    
    使用手机号和密码进行登录。
    
    Args:
        login_data: 登录数据
        auth_service: 认证服务
        
    Returns:
        ResponseModel[UserLoginResponse]: 登录结果
        
    Raises:
        HTTPException: 登录失败时抛出异常
    """
    try:
        result = await auth_service.login_with_password(login_data)
        
        if not result.success:
            raise HTTPException(
                status_code=401,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"密码登录API异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/wechat-login", response_model=ResponseModel[UserLoginResponse])
async def wechat_login(
    wechat_code: str = Body(..., description="微信登录code"),
    user_info: Optional[Dict[str, Any]] = Body(None, description="微信用户信息"),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[UserLoginResponse]:
    """微信登录
    
    使用微信小程序code进行登录，如果用户不存在则自动注册。
    
    Args:
        wechat_code: 微信登录code
        user_info: 微信用户信息（可选）
        auth_service: 认证服务
        
    Returns:
        ResponseModel[UserLoginResponse]: 登录结果
        
    Raises:
        HTTPException: 登录失败时抛出异常
    """
    try:
        result = await auth_service.login_with_wechat(wechat_code, user_info)
        
        if not result.success:
            raise HTTPException(
                status_code=401,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"微信登录API异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"微信登录失败: {str(e)}"
        )


@router.post("/refresh", response_model=ResponseModel[Dict[str, str]])
async def refresh_token(
    refresh_token: str = Body(..., description="刷新令牌"),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[Dict[str, str]]:
    """刷新访问令牌
    
    使用刷新令牌获取新的访问令牌。
    
    Args:
        refresh_token: 刷新令牌
        auth_service: 认证服务
        
    Returns:
        ResponseModel[Dict[str, str]]: 新的访问令牌
        
    Raises:
        HTTPException: 刷新失败时抛出异常
    """
    try:
        result = await auth_service.refresh_token(refresh_token)
        
        if not result.success:
            raise HTTPException(
                status_code=401,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新令牌API异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"令牌刷新失败: {str(e)}"
        )


@router.post("/logout", response_model=ResponseModel[bool])
async def logout(
    current_user_payload = Depends(require_active_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[bool]:
    """用户登出
    
    登出当前用户。
    
    Args:
        current_user: 当前用户
        auth_service: 认证服务
        
    Returns:
        ResponseModel[bool]: 登出结果
        
    Raises:
        HTTPException: 登出失败时抛出异常
    """
    try:
        result = await auth_service.logout(current_user.id)
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登出API异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"登出失败: {str(e)}"
        )


@router.get("/me", response_model=ResponseModel[User])
async def get_current_user_info(
    current_user_payload = Depends(require_active_user)
) -> ResponseModel[User]:
    """获取当前用户信息
    
    获取当前登录用户的详细信息。
    
    Args:
        current_user: 当前用户
        
    Returns:
        ResponseModel[User]: 用户信息
    """
    return ResponseModel(
        success=True,
        message="获取用户信息成功",
        data=current_user
    )


@router.put("/me", response_model=ResponseModel[User])
async def update_current_user(
    update_data: UserUpdate,
    current_user_payload = Depends(require_active_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[User]:
    """更新当前用户信息
    
    更新当前登录用户的资料信息。
    
    Args:
        update_data: 更新数据
        current_user: 当前用户
        auth_service: 认证服务
        
    Returns:
        ResponseModel[User]: 更新后的用户信息
        
    Raises:
        HTTPException: 更新失败时抛出异常
    """
    try:
        result = await auth_service.update_profile(current_user.id, update_data)
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息API异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"更新失败: {str(e)}"
        )


@router.post("/change-password", response_model=ResponseModel[bool])
async def change_password(
    old_password: str = Body(..., description="旧密码"),
    new_password: str = Body(..., description="新密码"),
    current_user_payload = Depends(require_active_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[bool]:
    """修改密码
    
    修改当前用户的登录密码。
    
    Args:
        old_password: 旧密码
        new_password: 新密码
        current_user: 当前用户
        auth_service: 认证服务
        
    Returns:
        ResponseModel[bool]: 修改结果
        
    Raises:
        HTTPException: 修改失败时抛出异常
    """
    try:
        result = await auth_service.change_password(
            current_user.id, old_password, new_password
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码API异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"密码修改失败: {str(e)}"
        )


@router.post("/verify-token")
async def verify_token(
    current_user_payload = Depends(require_active_user)
) -> ResponseModel[Dict[str, Any]]:
    """验证token有效性
    
    验证当前token是否有效。
    
    Args:
        current_user: 当前用户
        
    Returns:
        ResponseModel[Dict[str, Any]]: 验证结果
    """
    return ResponseModel(
        success=True,
        message="Token有效",
        data={
            "valid": True,
            "user_id": current_user.id,
            "role": current_user.role.value
        }
    )