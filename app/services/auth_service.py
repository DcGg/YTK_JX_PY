"""用户认证服务

实现用户注册、登录、JWT token管理、权限验证等功能。

Author: 云推客严选开发团队
Date: 2024
"""

import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from loguru import logger
from supabase import Client

from ..core.config import get_settings
from ..core.database import get_db_client
from ..core.security import SecurityManager, security_manager
from ..models.user import (
    User, UserCreate, UserUpdate, UserLogin, UserLoginResponse,
    UserRole, UserProfile
)
from ..models.common import ResponseModel
from .wechat_service import wechat_service

# 获取配置
settings = get_settings()


class AuthService:
    """用户认证服务类
    
    提供用户认证相关的所有功能。
    """
    
    def __init__(self, supabase: Client, security: SecurityManager):
        self.supabase = supabase
        self.security = security
    
    async def register_user(
        self, 
        user_data: UserCreate,
        wechat_code: Optional[str] = None
    ) -> ResponseModel[User]:
        """用户注册
        
        Args:
            user_data: 用户注册数据
            wechat_code: 微信登录code（可选）
            
        Returns:
            ResponseModel[User]: 注册结果
        """
        try:
            # 检查用户是否已存在
            if user_data.phone:
                existing_user = await self.get_user_by_phone(user_data.phone)
                if existing_user:
                    return ResponseModel(
                        success=False,
                        message="手机号已被注册",
                        data=None
                    )
            
            # 处理微信登录
            wechat_openid = None
            wechat_unionid = None
            if wechat_code:
                try:
                    wechat_data = await wechat_service.code_to_session(wechat_code)
                    wechat_openid = wechat_data.get("openid")
                    wechat_unionid = wechat_data.get("unionid")
                    
                    # 检查微信用户是否已存在
                    if wechat_openid:
                        existing_wechat_user = await self.get_user_by_wechat_openid(wechat_openid)
                        if existing_wechat_user:
                            return ResponseModel(
                                success=False,
                                message="微信用户已存在",
                                data=None
                            )
                except Exception as e:
                    logger.warning(f"微信登录处理失败: {e}")
            
            # 生成用户ID
            user_id = str(uuid.uuid4())
            
            # 密码加密（如果提供）
            hashed_password = None
            if user_data.password:
                hashed_password = self.security.hash_password(user_data.password)
            
            # 构造用户数据
            db_user_data = {
                "id": user_id,
                "phone": user_data.phone,
                "password_hash": hashed_password,
                "nickname": user_data.nickname,
                "avatar_url": user_data.avatar_url,
                "role": user_data.role.value,
                "wechat_openid": wechat_openid,
                "wechat_unionid": wechat_unionid,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 添加用户资料
            if user_data.profile:
                profile_data = user_data.profile.dict(exclude_unset=True)
                db_user_data.update(profile_data)
            
            # 插入用户数据
            result = self.supabase.table("users").insert(db_user_data).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="用户注册失败",
                    data=None
                )
            
            # 转换为User模型
            user = User(**result.data[0])
            
            logger.info(f"用户注册成功: {user.id}")
            return ResponseModel(
                success=True,
                message="注册成功",
                data=user
            )
            
        except Exception as e:
            logger.error(f"用户注册异常: {e}")
            return ResponseModel(
                success=False,
                message=f"注册失败: {str(e)}",
                data=None
            )
    
    async def login_with_password(
        self, 
        login_data: UserLogin
    ) -> ResponseModel[UserLoginResponse]:
        """密码登录
        
        Args:
            login_data: 登录数据
            
        Returns:
            ResponseModel[UserLoginResponse]: 登录结果
        """
        try:
            # 获取用户
            user = await self.get_user_by_phone(login_data.phone)
            if not user:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=None
                )
            
            # 验证密码
            if not user.password_hash or not self.security.verify_password(
                login_data.password, user.password_hash
            ):
                return ResponseModel(
                    success=False,
                    message="密码错误",
                    data=None
                )
            
            # 检查用户状态
            if not user.is_active:
                return ResponseModel(
                    success=False,
                    message="用户已被禁用",
                    data=None
                )
            
            # 生成token
            access_token = self.security.create_access_token(
                data={"sub": user.id, "role": user.role.value}
            )
            refresh_token = self.security.create_refresh_token(
                data={"sub": user.id}
            )
            
            # 更新最后登录时间
            await self.update_last_login(user.id)
            
            login_response = UserLoginResponse(
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer"
            )
            
            logger.info(f"用户密码登录成功: {user.id}")
            return ResponseModel(
                success=True,
                message="登录成功",
                data=login_response
            )
            
        except Exception as e:
            logger.error(f"密码登录异常: {e}")
            return ResponseModel(
                success=False,
                message=f"登录失败: {str(e)}",
                data=None
            )
    
    async def login_with_wechat(
        self, 
        wechat_code: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> ResponseModel[UserLoginResponse]:
        """微信登录
        
        Args:
            wechat_code: 微信登录code
            user_info: 微信用户信息（可选）
            
        Returns:
            ResponseModel[UserLoginResponse]: 登录结果
        """
        try:
            # 获取微信session信息
            wechat_data = await wechat_service.code_to_session(wechat_code)
            openid = wechat_data.get("openid")
            unionid = wechat_data.get("unionid")
            
            if not openid:
                return ResponseModel(
                    success=False,
                    message="微信登录失败：无法获取openid",
                    data=None
                )
            
            # 查找现有用户
            user = await self.get_user_by_wechat_openid(openid)
            
            if user:
                # 用户已存在，直接登录
                if not user.is_active:
                    return ResponseModel(
                        success=False,
                        message="用户已被禁用",
                        data=None
                    )
                
                # 更新微信信息（如果有变化）
                if user_info:
                    await self.update_wechat_info(user.id, user_info)
                    # 重新获取用户信息
                    user = await self.get_user_by_id(user.id)
            else:
                # 新用户，自动注册
                user_create_data = {
                    "role": UserRole.INFLUENCER,  # 默认为达人角色
                    "wechat_openid": openid,
                    "wechat_unionid": unionid
                }
                
                if user_info:
                    user_create_data.update({
                        "nickname": user_info.get("nickName"),
                        "avatar_url": user_info.get("avatarUrl")
                    })
                
                user_create = UserCreate(**user_create_data)
                register_result = await self.register_user(user_create)
                
                if not register_result.success:
                    return register_result
                
                user = register_result.data
            
            # 生成token
            access_token = self.security.create_access_token(
                data={"sub": user.id, "role": user.role.value}
            )
            refresh_token = self.security.create_refresh_token(
                data={"sub": user.id}
            )
            
            # 更新最后登录时间
            await self.update_last_login(user.id)
            
            login_response = UserLoginResponse(
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer"
            )
            
            logger.info(f"用户微信登录成功: {user.id}")
            return ResponseModel(
                success=True,
                message="登录成功",
                data=login_response
            )
            
        except Exception as e:
            logger.error(f"微信登录异常: {e}")
            return ResponseModel(
                success=False,
                message=f"微信登录失败: {str(e)}",
                data=None
            )
    
    async def refresh_token(self, refresh_token: str) -> ResponseModel[Dict[str, str]]:
        """刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            ResponseModel[Dict[str, str]]: 新的访问令牌
        """
        try:
            # 验证刷新令牌
            payload = self.security.verify_token(refresh_token)
            if not payload:
                return ResponseModel(
                    success=False,
                    message="刷新令牌无效",
                    data=None
                )
            
            user_id = payload.get("sub")
            if not user_id:
                return ResponseModel(
                    success=False,
                    message="刷新令牌格式错误",
                    data=None
                )
            
            # 获取用户信息
            user = await self.get_user_by_id(user_id)
            if not user or not user.is_active:
                return ResponseModel(
                    success=False,
                    message="用户不存在或已被禁用",
                    data=None
                )
            
            # 生成新的访问令牌
            new_access_token = self.security.create_access_token(
                data={"sub": user.id, "role": user.role.value}
            )
            
            return ResponseModel(
                success=True,
                message="令牌刷新成功",
                data={
                    "access_token": new_access_token,
                    "token_type": "bearer"
                }
            )
            
        except Exception as e:
            logger.error(f"刷新令牌异常: {e}")
            return ResponseModel(
                success=False,
                message=f"令牌刷新失败: {str(e)}",
                data=None
            )
    
    async def logout(self, user_id: str) -> ResponseModel[bool]:
        """用户登出
        
        Args:
            user_id: 用户ID
            
        Returns:
            ResponseModel[bool]: 登出结果
        """
        try:
            # 这里可以实现token黑名单机制
            # 目前只是记录日志
            logger.info(f"用户登出: {user_id}")
            
            return ResponseModel(
                success=True,
                message="登出成功",
                data=True
            )
            
        except Exception as e:
            logger.error(f"用户登出异常: {e}")
            return ResponseModel(
                success=False,
                message=f"登出失败: {str(e)}",
                data=False
            )
    
    async def update_profile(
        self, 
        user_id: str, 
        update_data: UserUpdate
    ) -> ResponseModel[User]:
        """更新用户资料
        
        Args:
            user_id: 用户ID
            update_data: 更新数据
            
        Returns:
            ResponseModel[User]: 更新结果
        """
        try:
            # 构造更新数据
            db_update_data = update_data.dict(exclude_unset=True)
            db_update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # 密码加密
            if "password" in db_update_data:
                db_update_data["password_hash"] = self.security.hash_password(
                    db_update_data.pop("password")
                )
            
            # 更新用户
            result = self.supabase.table("users").update(
                db_update_data
            ).eq("id", user_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=None
                )
            
            user = User(**result.data[0])
            
            logger.info(f"用户资料更新成功: {user_id}")
            return ResponseModel(
                success=True,
                message="资料更新成功",
                data=user
            )
            
        except Exception as e:
            logger.error(f"更新用户资料异常: {e}")
            return ResponseModel(
                success=False,
                message=f"资料更新失败: {str(e)}",
                data=None
            )
    
    async def change_password(
        self, 
        user_id: str, 
        old_password: str, 
        new_password: str
    ) -> ResponseModel[bool]:
        """修改密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            ResponseModel[bool]: 修改结果
        """
        try:
            # 获取用户
            user = await self.get_user_by_id(user_id)
            if not user:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=False
                )
            
            # 验证旧密码
            if not user.password_hash or not self.security.verify_password(
                old_password, user.password_hash
            ):
                return ResponseModel(
                    success=False,
                    message="旧密码错误",
                    data=False
                )
            
            # 更新密码
            new_password_hash = self.security.hash_password(new_password)
            result = self.supabase.table("users").update({
                "password_hash": new_password_hash,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="密码修改失败",
                    data=False
                )
            
            logger.info(f"用户密码修改成功: {user_id}")
            return ResponseModel(
                success=True,
                message="密码修改成功",
                data=True
            )
            
        except Exception as e:
            logger.error(f"修改密码异常: {e}")
            return ResponseModel(
                success=False,
                message=f"密码修改失败: {str(e)}",
                data=False
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[User]: 用户信息
        """
        try:
            result = self.supabase.table("users").select("*").eq(
                "id", user_id
            ).execute()
            
            if result.data:
                return User(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"获取用户异常: {e}")
            return None
    
    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        """根据手机号获取用户
        
        Args:
            phone: 手机号
            
        Returns:
            Optional[User]: 用户信息
        """
        try:
            result = self.supabase.table("users").select("*").eq(
                "phone", phone
            ).execute()
            
            if result.data:
                return User(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"根据手机号获取用户异常: {e}")
            return None
    
    async def get_user_by_wechat_openid(self, openid: str) -> Optional[User]:
        """根据微信openid获取用户
        
        Args:
            openid: 微信openid
            
        Returns:
            Optional[User]: 用户信息
        """
        try:
            result = self.supabase.table("users").select("*").eq(
                "wechat_openid", openid
            ).execute()
            
            if result.data:
                return User(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"根据微信openid获取用户异常: {e}")
            return None
    
    async def update_last_login(self, user_id: str) -> bool:
        """更新最后登录时间
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            result = self.supabase.table("users").update({
                "last_login_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"更新最后登录时间异常: {e}")
            return False
    
    async def update_wechat_info(
        self, 
        user_id: str, 
        wechat_info: Dict[str, Any]
    ) -> bool:
        """更新微信信息
        
        Args:
            user_id: 用户ID
            wechat_info: 微信信息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 更新昵称和头像
            if "nickName" in wechat_info:
                update_data["nickname"] = wechat_info["nickName"]
            if "avatarUrl" in wechat_info:
                update_data["avatar_url"] = wechat_info["avatarUrl"]
            
            result = self.supabase.table("users").update(
                update_data
            ).eq("id", user_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"更新微信信息异常: {e}")
            return False
    
    async def verify_user_permission(
        self, 
        user_id: str, 
        required_role: UserRole
    ) -> bool:
        """验证用户权限
        
        Args:
            user_id: 用户ID
            required_role: 所需角色
            
        Returns:
            bool: 是否有权限
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user or not user.is_active:
                return False
            
            # 角色权限层级：ADMIN > MERCHANT > LEADER > INFLUENCER
            role_hierarchy = {
                UserRole.INFLUENCER: 1,
                UserRole.LEADER: 2,
                UserRole.MERCHANT: 3,
                UserRole.ADMIN: 4
            }
            
            user_level = role_hierarchy.get(user.role, 0)
            required_level = role_hierarchy.get(required_role, 0)
            
            return user_level >= required_level
            
        except Exception as e:
            logger.error(f"验证用户权限异常: {e}")
            return False


# 依赖注入函数
def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    supabase = get_db_client()
    security = security_manager
    return AuthService(supabase, security)