"""用户关系数据模型

定义用户之间的关系模型，包括达人与团长的绑定关系、推荐关系等。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from decimal import Decimal
from datetime import datetime
from pydantic import Field, validator
from uuid import UUID

from .common import BaseModel, TimestampMixin, UUIDMixin


class RelationshipType(str, Enum):
    """关系类型枚举"""
    
    BINDING = "binding"              # 绑定关系（达人绑定团长）
    REFERRAL = "referral"            # 推荐关系
    PARTNERSHIP = "partnership"      # 合作关系
    FOLLOW = "follow"                # 关注关系


class RelationshipStatus(str, Enum):
    """关系状态枚举"""
    
    ACTIVE = "active"                # 活跃
    INACTIVE = "inactive"            # 非活跃
    PENDING = "pending"              # 待确认
    REJECTED = "rejected"            # 已拒绝
    EXPIRED = "expired"              # 已过期
    CANCELLED = "cancelled"          # 已取消


class CommissionRule(BaseModel):
    """佣金规则模型"""
    
    commission_rate: Decimal = Field(
        description="佣金比例",
        ge=0,
        le=1,
        decimal_places=4,
        example=0.1000
    )
    min_order_amount: Optional[Decimal] = Field(
        None,
        description="最小订单金额",
        ge=0,
        decimal_places=2,
        example=100.00
    )
    max_commission: Optional[Decimal] = Field(
        None,
        description="最大佣金金额",
        ge=0,
        decimal_places=2,
        example=1000.00
    )
    effective_from: datetime = Field(
        description="生效开始时间",
        example="2024-01-01T00:00:00Z"
    )
    effective_to: Optional[datetime] = Field(
        None,
        description="生效结束时间",
        example="2024-12-31T23:59:59Z"
    )
    
    @validator('commission_rate')
    def validate_commission_rate(cls, v):
        """验证佣金比例"""
        if v < 0 or v > 1:
            raise ValueError('佣金比例必须在0-1之间')
        return v


class RelationshipBase(BaseModel):
    """关系基础模型"""
    
    from_user_id: UUID = Field(
        description="发起用户ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    to_user_id: UUID = Field(
        description="目标用户ID",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    relationship_type: RelationshipType = Field(
        description="关系类型",
        example=RelationshipType.BINDING
    )
    status: RelationshipStatus = Field(
        RelationshipStatus.PENDING,
        description="关系状态"
    )
    commission_rule: Optional[CommissionRule] = Field(
        None,
        description="佣金规则"
    )
    notes: Optional[str] = Field(
        None,
        description="备注信息",
        max_length=500,
        example="达人主要推广美妆类产品"
    )
    
    @validator('from_user_id', 'to_user_id')
    def validate_user_ids(cls, v, values):
        """验证用户ID"""
        if 'from_user_id' in values and v == values['from_user_id']:
            raise ValueError('发起用户和目标用户不能相同')
        return v


class RelationshipCreate(RelationshipBase):
    """创建关系模型"""
    pass


class RelationshipUpdate(BaseModel):
    """更新关系模型"""
    
    status: Optional[RelationshipStatus] = Field(
        None,
        description="关系状态"
    )
    commission_rule: Optional[CommissionRule] = Field(
        None,
        description="佣金规则"
    )
    notes: Optional[str] = Field(
        None,
        description="备注信息",
        max_length=500
    )


class UserRelationship(UUIDMixin, RelationshipBase, TimestampMixin):
    """用户关系完整模型"""
    
    confirmed_at: Optional[datetime] = Field(
        None,
        description="确认时间"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="过期时间"
    )
    last_activity_at: Optional[datetime] = Field(
        None,
        description="最后活动时间"
    )
    total_orders: int = Field(
        0,
        description="总订单数",
        ge=0,
        example=50
    )
    total_amount: Decimal = Field(
        Decimal('0.00'),
        description="总订单金额",
        ge=0,
        decimal_places=2,
        example=5000.00
    )
    total_commission: Decimal = Field(
        Decimal('0.00'),
        description="总佣金金额",
        ge=0,
        decimal_places=2,
        example=500.00
    )
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "from_user_id": "123e4567-e89b-12d3-a456-426614174001",
                "to_user_id": "123e4567-e89b-12d3-a456-426614174002",
                "relationship_type": "binding",
                "status": "active",
                "total_orders": 50,
                "total_amount": 5000.00,
                "total_commission": 500.00,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class RelationshipResponse(UserRelationship):
    """关系响应模型
    
    用于API响应，包含关联用户信息。
    """
    
    from_user_name: Optional[str] = Field(
        None,
        description="发起用户姓名",
        example="张三"
    )
    from_user_type: Optional[str] = Field(
        None,
        description="发起用户类型",
        example="influencer"
    )
    from_user_avatar: Optional[str] = Field(
        None,
        description="发起用户头像",
        example="https://example.com/avatar/user1.jpg"
    )
    to_user_name: Optional[str] = Field(
        None,
        description="目标用户姓名",
        example="李四"
    )
    to_user_type: Optional[str] = Field(
        None,
        description="目标用户类型",
        example="leader"
    )
    to_user_avatar: Optional[str] = Field(
        None,
        description="目标用户头像",
        example="https://example.com/avatar/user2.jpg"
    )
    can_modify: bool = Field(
        True,
        description="是否可以修改",
        example=True
    )
    can_cancel: bool = Field(
        True,
        description="是否可以取消",
        example=True
    )
    days_since_created: Optional[int] = Field(
        None,
        description="创建天数",
        example=30
    )
    days_until_expiry: Optional[int] = Field(
        None,
        description="距离过期天数",
        example=335
    )
    recent_orders: Optional[int] = Field(
        None,
        description="近期订单数（30天内）",
        example=5
    )
    recent_amount: Optional[Decimal] = Field(
        None,
        description="近期订单金额（30天内）",
        example=500.00
    )


class RelationshipListResponse(BaseModel):
    """关系列表响应模型"""
    
    relationships: List[RelationshipResponse] = Field(
        description="关系列表"
    )
    total: int = Field(
        description="总数量",
        example=100
    )
    page: int = Field(
        description="当前页码",
        example=1
    )
    size: int = Field(
        description="每页数量",
        example=20
    )
    pages: int = Field(
        description="总页数",
        example=5
    )


class RelationshipSearch(BaseModel):
    """关系搜索模型"""
    
    from_user_id: Optional[UUID] = Field(
        None,
        description="发起用户ID"
    )
    to_user_id: Optional[UUID] = Field(
        None,
        description="目标用户ID"
    )
    relationship_type: Optional[RelationshipType] = Field(
        None,
        description="关系类型"
    )
    status: Optional[RelationshipStatus] = Field(
        None,
        description="关系状态"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="开始日期"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="结束日期"
    )
    keyword: Optional[str] = Field(
        None,
        description="搜索关键词（用户名）",
        example="张三"
    )
    min_orders: Optional[int] = Field(
        None,
        description="最小订单数",
        ge=0,
        example=10
    )
    min_amount: Optional[Decimal] = Field(
        None,
        description="最小订单金额",
        ge=0,
        example=1000.00
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="排序字段",
        example="total_amount"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="排序方向",
        example="desc"
    )


class RelationshipStatistics(BaseModel):
    """关系统计模型"""
    
    total_relationships: int = Field(
        description="关系总数",
        example=1000
    )
    active_relationships: int = Field(
        description="活跃关系数",
        example=800
    )
    pending_relationships: int = Field(
        description="待确认关系数",
        example=50
    )
    binding_relationships: int = Field(
        description="绑定关系数",
        example=600
    )
    referral_relationships: int = Field(
        description="推荐关系数",
        example=300
    )
    total_commission_paid: Decimal = Field(
        description="总佣金支付金额",
        example=100000.00
    )
    average_commission_rate: float = Field(
        description="平均佣金比例",
        example=0.08
    )
    top_performers: List[Dict[str, Any]] = Field(
        description="顶级表现者",
        example=[
            {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_name": "张三",
                "total_orders": 100,
                "total_amount": 10000.00,
                "total_commission": 1000.00
            }
        ]
    )
    relationship_types_distribution: List[Dict[str, Any]] = Field(
        description="关系类型分布",
        example=[
            {"type": "binding", "count": 600},
            {"type": "referral", "count": 300},
            {"type": "partnership", "count": 80},
            {"type": "follow", "count": 20}
        ]
    )
    monthly_trends: List[Dict[str, Any]] = Field(
        description="月度趋势",
        example=[
            {"month": "2024-01", "new_relationships": 50, "total_orders": 500},
            {"month": "2024-02", "new_relationships": 60, "total_orders": 600}
        ]
    )


class RelationshipRequest(BaseModel):
    """关系请求模型"""
    
    to_user_id: UUID = Field(
        description="目标用户ID",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    relationship_type: RelationshipType = Field(
        description="关系类型",
        example=RelationshipType.BINDING
    )
    message: Optional[str] = Field(
        None,
        description="请求消息",
        max_length=200,
        example="希望能与您建立合作关系"
    )
    commission_rate: Optional[Decimal] = Field(
        None,
        description="建议佣金比例",
        ge=0,
        le=1,
        decimal_places=4,
        example=0.1000
    )


class RelationshipApproval(BaseModel):
    """关系审批模型"""
    
    relationship_id: UUID = Field(
        description="关系ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    approved: bool = Field(
        description="是否同意",
        example=True
    )
    commission_rule: Optional[CommissionRule] = Field(
        None,
        description="佣金规则"
    )
    notes: Optional[str] = Field(
        None,
        description="备注信息",
        max_length=500,
        example="同意建立合作关系"
    )
    expires_days: Optional[int] = Field(
        365,
        description="有效期天数",
        gt=0,
        le=3650,
        example=365
    )


class RelationshipBatchOperation(BaseModel):
    """关系批量操作模型"""
    
    relationship_ids: List[UUID] = Field(
        description="关系ID列表",
        min_items=1
    )
    operation: str = Field(
        description="操作类型",
        example="approve"  # approve, reject, activate, deactivate, cancel
    )
    commission_rule: Optional[CommissionRule] = Field(
        None,
        description="佣金规则"
    )
    notes: Optional[str] = Field(
        None,
        description="操作备注",
        max_length=500,
        example="批量审批通过"
    )
    
    @validator('relationship_ids')
    def validate_relationship_ids(cls, v):
        """验证关系ID列表"""
        if not v:
            raise ValueError('关系ID列表不能为空')
        return v


class UserBindingInfo(BaseModel):
    """用户绑定信息模型"""
    
    user_id: UUID = Field(
        description="用户ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    user_name: str = Field(
        description="用户姓名",
        example="张三"
    )
    user_type: str = Field(
        description="用户类型",
        example="influencer"
    )
    avatar: Optional[str] = Field(
        None,
        description="用户头像",
        example="https://example.com/avatar/user.jpg"
    )
    binding_date: datetime = Field(
        description="绑定时间",
        example="2024-01-01T00:00:00Z"
    )
    status: RelationshipStatus = Field(
        description="关系状态",
        example=RelationshipStatus.ACTIVE
    )
    total_orders: int = Field(
        description="总订单数",
        example=50
    )
    total_amount: Decimal = Field(
        description="总订单金额",
        example=5000.00
    )
    total_commission: Decimal = Field(
        description="总佣金金额",
        example=500.00
    )
    commission_rate: Optional[Decimal] = Field(
        None,
        description="佣金比例",
        example=0.1000
    )
    last_order_date: Optional[datetime] = Field(
        None,
        description="最后下单时间",
        example="2024-01-15T00:00:00Z"
    )


class TeamPerformance(BaseModel):
    """团队业绩模型"""
    
    leader_id: UUID = Field(
        description="团长ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    leader_name: str = Field(
        description="团长姓名",
        example="李四"
    )
    total_influencers: int = Field(
        description="绑定达人总数",
        example=20
    )
    active_influencers: int = Field(
        description="活跃达人数",
        example=15
    )
    total_orders: int = Field(
        description="团队总订单数",
        example=500
    )
    total_amount: Decimal = Field(
        description="团队总订单金额",
        example=50000.00
    )
    total_commission: Decimal = Field(
        description="团队总佣金",
        example=5000.00
    )
    average_order_value: Decimal = Field(
        description="平均订单价值",
        example=100.00
    )
    conversion_rate: float = Field(
        description="转化率",
        example=0.15
    )
    growth_rate: float = Field(
        description="增长率",
        example=0.20
    )
    top_influencers: List[UserBindingInfo] = Field(
        description="顶级达人列表"
    )
    monthly_performance: List[Dict[str, Any]] = Field(
        description="月度业绩",
        example=[
            {"month": "2024-01", "orders": 100, "amount": 10000.00},
            {"month": "2024-02", "orders": 120, "amount": 12000.00}
        ]
    )