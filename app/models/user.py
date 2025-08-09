"""用户数据模型

定义用户相关的数据模型，包括商家、团长、达人等不同角色。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import Dict, Any, Optional
from enum import Enum
from pydantic import Field, validator
from uuid import UUID

from .common import BaseModel, TimestampMixin, UUIDMixin


class UserRole(str, Enum):
    """用户角色枚举"""
    
    MERCHANT = "merchant"      # 商家
    LEADER = "leader"          # 团长
    INFLUENCER = "influencer"  # 达人


class UserProfile(BaseModel):
    """用户档案数据模型
    
    存储用户的扩展信息，根据角色不同包含不同字段。
    """
    
    # 商家专用字段
    company: Optional[str] = Field(
        None,
        description="公司名称",
        example="云推客科技有限公司"
    )
    business_license: Optional[str] = Field(
        None,
        description="营业执照号",
        example="91110000000000000X"
    )
    verified: Optional[bool] = Field(
        False,
        description="是否已认证",
        example=True
    )
    
    # 团长专用字段
    team_name: Optional[str] = Field(
        None,
        description="团队名称",
        example="精选好物团"
    )
    wechat_id: Optional[str] = Field(
        None,
        description="微信号",
        example="leader001"
    )
    team_size: Optional[int] = Field(
        0,
        description="团队规模",
        example=50
    )
    
    # 达人专用字段
    fans_count: Optional[int] = Field(
        0,
        description="粉丝数量",
        example=10000
    )
    category: Optional[str] = Field(
        None,
        description="专业领域",
        example="美妆护肤"
    )
    platform_accounts: Optional[Dict[str, str]] = Field(
        None,
        description="平台账号信息",
        example={
            "douyin": "@beauty_expert",
            "xiaohongshu": "@makeup_guru"
        }
    )
    
    # 通用字段
    bio: Optional[str] = Field(
        None,
        description="个人简介",
        example="专注美妆护肤，为您推荐优质好物"
    )
    location: Optional[str] = Field(
        None,
        description="所在地区",
        example="北京市朝阳区"
    )
    tags: Optional[list] = Field(
        None,
        description="标签列表",
        example=["美妆", "护肤", "时尚"]
    )


class UserBase(BaseModel):
    """用户基础模型"""
    
    wechat_openid: str = Field(
        description="微信OpenID",
        example="oU9Xp5q2J8X9Y7Z6W5V4U3T2S1R0"
    )
    phone: Optional[str] = Field(
        None,
        description="手机号码",
        example="13800138000",
        pattern=r"^1[3-9]\d{9}$"
    )
    nickname: str = Field(
        description="用户昵称",
        min_length=1,
        max_length=50,
        example="张三"
    )
    avatar_url: Optional[str] = Field(
        None,
        description="头像URL",
        example="https://example.com/avatar.jpg"
    )
    role: UserRole = Field(
        description="用户角色",
        example=UserRole.MERCHANT
    )
    profile_data: Optional[UserProfile] = Field(
        None,
        description="用户档案数据"
    )


class UserCreate(UserBase):
    """创建用户模型"""
    
    @validator('wechat_openid')
    def validate_wechat_openid(cls, v):
        """验证微信OpenID格式"""
        if not v or len(v) < 10:
            raise ValueError('微信OpenID格式不正确')
        return v
    
    @validator('nickname')
    def validate_nickname(cls, v):
        """验证昵称"""
        if not v or not v.strip():
            raise ValueError('昵称不能为空')
        return v.strip()


class UserUpdate(BaseModel):
    """更新用户模型"""
    
    phone: Optional[str] = Field(
        None,
        description="手机号码",
        pattern=r"^1[3-9]\d{9}$"
    )
    nickname: Optional[str] = Field(
        None,
        description="用户昵称",
        min_length=1,
        max_length=50
    )
    avatar_url: Optional[str] = Field(
        None,
        description="头像URL"
    )
    profile_data: Optional[UserProfile] = Field(
        None,
        description="用户档案数据"
    )
    
    @validator('nickname')
    def validate_nickname(cls, v):
        """验证昵称"""
        if v is not None and (not v or not v.strip()):
            raise ValueError('昵称不能为空')
        return v.strip() if v else v


class User(UUIDMixin, UserBase, TimestampMixin):
    """用户完整模型"""
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "wechat_openid": "oU9Xp5q2J8X9Y7Z6W5V4U3T2S1R0",
                "phone": "13800138000",
                "nickname": "张三",
                "avatar_url": "https://example.com/avatar.jpg",
                "role": "merchant",
                "profile_data": {
                    "company": "云推客科技有限公司",
                    "verified": True,
                    "bio": "专业的电商服务提供商"
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class UserResponse(User):
    """用户响应模型
    
    用于API响应，可能包含额外的计算字段。
    """
    
    # 可以添加计算字段
    total_products: Optional[int] = Field(
        None,
        description="商品总数（仅商家）",
        example=25
    )
    total_orders: Optional[int] = Field(
        None,
        description="订单总数",
        example=100
    )
    commission_earned: Optional[float] = Field(
        None,
        description="累计佣金（仅达人/团长）",
        example=1500.50
    )
    team_members: Optional[int] = Field(
        None,
        description="团队成员数（仅团长）",
        example=30
    )


class UserLogin(BaseModel):
    """用户登录模型"""
    
    wechat_code: str = Field(
        description="微信授权码",
        example="061234567890abcdef"
    )
    user_info: Optional[Dict[str, Any]] = Field(
        None,
        description="用户信息（可选）",
        example={
            "nickname": "张三",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    )


class UserLoginResponse(BaseModel):
    """用户登录响应模型"""
    
    access_token: str = Field(
        description="访问令牌",
        example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    )
    token_type: str = Field(
        "bearer",
        description="令牌类型"
    )
    expires_in: int = Field(
        description="过期时间（秒）",
        example=3600
    )
    user: UserResponse = Field(
        description="用户信息"
    )
    is_new_user: bool = Field(
        description="是否为新用户",
        example=False
    )


class UserStatistics(BaseModel):
    """用户统计模型"""
    
    total_users: int = Field(
        description="用户总数",
        example=1000
    )
    merchants_count: int = Field(
        description="商家数量",
        example=100
    )
    leaders_count: int = Field(
        description="团长数量",
        example=200
    )
    influencers_count: int = Field(
        description="达人数量",
        example=700
    )
    active_users: int = Field(
        description="活跃用户数",
        example=800
    )
    new_users_today: int = Field(
        description="今日新增用户",
        example=10
    )
    growth_rate: float = Field(
        description="增长率",
        example=0.15
    )