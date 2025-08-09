"""申样数据模型

定义申样相关的数据模型，包括申样请求、状态跟踪、审核处理等。

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


class SampleStatus(str, Enum):
    """申样状态枚举"""
    
    PENDING = "pending"              # 待审核
    APPROVED = "approved"            # 已通过
    REJECTED = "rejected"            # 已拒绝
    SHIPPED = "shipped"              # 已发货
    DELIVERED = "delivered"          # 已送达
    REVIEWED = "reviewed"            # 已评价
    CANCELLED = "cancelled"          # 已取消
    EXPIRED = "expired"              # 已过期


class SampleType(str, Enum):
    """申样类型枚举"""
    
    FREE = "free"                    # 免费试用
    PAID = "paid"                    # 付费试用
    DEPOSIT = "deposit"              # 押金试用
    EXCHANGE = "exchange"            # 积分兑换


class ReviewRating(int, Enum):
    """评价等级枚举"""
    
    ONE_STAR = 1      # 1星
    TWO_STAR = 2      # 2星
    THREE_STAR = 3    # 3星
    FOUR_STAR = 4     # 4星
    FIVE_STAR = 5     # 5星


class SampleReview(BaseModel):
    """申样评价模型"""
    
    rating: ReviewRating = Field(
        description="评分",
        example=ReviewRating.FIVE_STAR
    )
    content: str = Field(
        description="评价内容",
        min_length=10,
        max_length=1000,
        example="产品质量很好，使用体验不错，值得推荐！"
    )
    images: List[str] = Field(
        default_factory=list,
        description="评价图片",
        example=[
            "https://example.com/review/image1.jpg",
            "https://example.com/review/image2.jpg"
        ]
    )
    video_url: Optional[str] = Field(
        None,
        description="评价视频",
        example="https://example.com/review/video.mp4"
    )
    is_public: bool = Field(
        True,
        description="是否公开",
        example=True
    )
    
    @validator('content')
    def validate_content(cls, v):
        """验证评价内容"""
        if not v or not v.strip():
            raise ValueError('评价内容不能为空')
        return v.strip()


class SampleShippingInfo(BaseModel):
    """申样物流信息模型"""
    
    recipient_name: str = Field(
        description="收货人姓名",
        min_length=1,
        max_length=50,
        example="张三"
    )
    phone: str = Field(
        description="联系电话",
        pattern=r"^1[3-9]\d{9}$",
        example="13800138000"
    )
    province: str = Field(
        description="省份",
        example="北京市"
    )
    city: str = Field(
        description="城市",
        example="北京市"
    )
    district: str = Field(
        description="区县",
        example="朝阳区"
    )
    street: str = Field(
        description="详细地址",
        min_length=1,
        max_length=200,
        example="三里屯街道工体北路8号"
    )
    postal_code: Optional[str] = Field(
        None,
        description="邮政编码",
        pattern=r"^\d{6}$",
        example="100027"
    )
    tracking_number: Optional[str] = Field(
        None,
        description="快递单号",
        example="SF1234567890"
    )
    shipping_company: Optional[str] = Field(
        None,
        description="快递公司",
        example="顺丰速运"
    )


class SampleBase(BaseModel):
    """申样基础模型"""
    
    applicant_id: UUID = Field(
        description="申请人ID（达人或团长）",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    product_id: UUID = Field(
        description="商品ID",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    merchant_id: UUID = Field(
        description="商家ID",
        example="123e4567-e89b-12d3-a456-426614174002"
    )
    sample_type: SampleType = Field(
        description="申样类型",
        example=SampleType.FREE
    )
    quantity: int = Field(
        description="申请数量",
        gt=0,
        le=10,
        example=1
    )
    application_reason: str = Field(
        description="申请理由",
        min_length=10,
        max_length=500,
        example="我是美妆博主，拥有10万粉丝，希望能试用贵公司的护肤产品并制作评测视频"
    )
    expected_review_date: Optional[datetime] = Field(
        None,
        description="预期评价时间",
        example="2024-01-15T00:00:00Z"
    )
    shipping_info: SampleShippingInfo = Field(
        description="收货信息"
    )
    deposit_amount: Optional[Decimal] = Field(
        None,
        description="押金金额",
        ge=0,
        decimal_places=2,
        example=100.00
    )
    
    @validator('application_reason')
    def validate_application_reason(cls, v):
        """验证申请理由"""
        if not v or not v.strip():
            raise ValueError('申请理由不能为空')
        return v.strip()
    
    @validator('quantity')
    def validate_quantity(cls, v):
        """验证申请数量"""
        if v <= 0:
            raise ValueError('申请数量必须大于0')
        if v > 10:
            raise ValueError('申请数量不能超过10')
        return v


class SampleCreate(SampleBase):
    """创建申样模型"""
    pass


class SampleUpdate(BaseModel):
    """更新申样模型"""
    
    status: Optional[SampleStatus] = Field(
        None,
        description="申样状态"
    )
    approval_reason: Optional[str] = Field(
        None,
        description="审核理由",
        max_length=500,
        example="申请人资质符合要求，同意发放样品"
    )
    shipping_info: Optional[SampleShippingInfo] = Field(
        None,
        description="收货信息"
    )
    tracking_number: Optional[str] = Field(
        None,
        description="快递单号"
    )
    shipping_company: Optional[str] = Field(
        None,
        description="快递公司"
    )
    review: Optional[SampleReview] = Field(
        None,
        description="评价信息"
    )


class Sample(UUIDMixin, SampleBase, TimestampMixin):
    """申样完整模型"""
    
    sample_number: str = Field(
        description="申样编号",
        example="SAMPLE202401010001"
    )
    status: SampleStatus = Field(
        SampleStatus.PENDING,
        description="申样状态"
    )
    approval_reason: Optional[str] = Field(
        None,
        description="审核理由"
    )
    approved_at: Optional[datetime] = Field(
        None,
        description="审核时间"
    )
    approved_by: Optional[UUID] = Field(
        None,
        description="审核人ID"
    )
    shipped_at: Optional[datetime] = Field(
        None,
        description="发货时间"
    )
    delivered_at: Optional[datetime] = Field(
        None,
        description="送达时间"
    )
    review: Optional[SampleReview] = Field(
        None,
        description="评价信息"
    )
    reviewed_at: Optional[datetime] = Field(
        None,
        description="评价时间"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="过期时间"
    )
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "applicant_id": "123e4567-e89b-12d3-a456-426614174001",
                "product_id": "123e4567-e89b-12d3-a456-426614174002",
                "merchant_id": "123e4567-e89b-12d3-a456-426614174003",
                "sample_number": "SAMPLE202401010001",
                "sample_type": "free",
                "quantity": 1,
                "status": "pending",
                "application_reason": "我是美妆博主，希望试用产品",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class SampleResponse(Sample):
    """申样响应模型
    
    用于API响应，包含关联数据。
    """
    
    applicant_name: Optional[str] = Field(
        None,
        description="申请人姓名",
        example="张三"
    )
    applicant_type: Optional[str] = Field(
        None,
        description="申请人类型",
        example="influencer"
    )
    product_title: Optional[str] = Field(
        None,
        description="商品标题",
        example="高端护肤精华液 50ml"
    )
    product_image: Optional[str] = Field(
        None,
        description="商品图片",
        example="https://example.com/product/image.jpg"
    )
    product_price: Optional[Decimal] = Field(
        None,
        description="商品价格",
        example=199.00
    )
    merchant_name: Optional[str] = Field(
        None,
        description="商家名称",
        example="云推客科技"
    )
    approver_name: Optional[str] = Field(
        None,
        description="审核人姓名",
        example="李四"
    )
    can_cancel: bool = Field(
        True,
        description="是否可以取消",
        example=True
    )
    can_review: bool = Field(
        False,
        description="是否可以评价",
        example=False
    )
    days_since_application: Optional[int] = Field(
        None,
        description="申请天数",
        example=5
    )
    days_until_expiry: Optional[int] = Field(
        None,
        description="距离过期天数",
        example=25
    )


class SampleListResponse(BaseModel):
    """申样列表响应模型"""
    
    samples: List[SampleResponse] = Field(
        description="申样列表"
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


class SampleSearch(BaseModel):
    """申样搜索模型"""
    
    sample_number: Optional[str] = Field(
        None,
        description="申样编号",
        example="SAMPLE202401010001"
    )
    applicant_id: Optional[UUID] = Field(
        None,
        description="申请人ID"
    )
    product_id: Optional[UUID] = Field(
        None,
        description="商品ID"
    )
    merchant_id: Optional[UUID] = Field(
        None,
        description="商家ID"
    )
    sample_type: Optional[SampleType] = Field(
        None,
        description="申样类型"
    )
    status: Optional[SampleStatus] = Field(
        None,
        description="申样状态"
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
        description="搜索关键词",
        example="护肤"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="排序字段",
        example="created_at"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="排序方向",
        example="desc"
    )


class SampleStatistics(BaseModel):
    """申样统计模型"""
    
    total_samples: int = Field(
        description="申样总数",
        example=1000
    )
    pending_samples: int = Field(
        description="待审核申样数",
        example=50
    )
    approved_samples: int = Field(
        description="已通过申样数",
        example=800
    )
    rejected_samples: int = Field(
        description="已拒绝申样数",
        example=100
    )
    shipped_samples: int = Field(
        description="已发货申样数",
        example=700
    )
    reviewed_samples: int = Field(
        description="已评价申样数",
        example=600
    )
    approval_rate: float = Field(
        description="通过率",
        example=0.80
    )
    review_rate: float = Field(
        description="评价率",
        example=0.75
    )
    average_review_rating: float = Field(
        description="平均评分",
        example=4.5
    )
    total_deposit: Decimal = Field(
        description="总押金金额",
        example=50000.00
    )
    sample_types_distribution: List[Dict[str, Any]] = Field(
        description="申样类型分布",
        example=[
            {"type": "free", "count": 600},
            {"type": "paid", "count": 200},
            {"type": "deposit", "count": 150},
            {"type": "exchange", "count": 50}
        ]
    )
    monthly_trends: List[Dict[str, Any]] = Field(
        description="月度趋势",
        example=[
            {"month": "2024-01", "applications": 100, "approvals": 80},
            {"month": "2024-02", "applications": 120, "approvals": 95}
        ]
    )
    top_products: List[Dict[str, Any]] = Field(
        description="热门申样商品",
        example=[
            {
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "product_title": "高端护肤精华液",
                "sample_count": 50
            }
        ]
    )


class SampleBatchOperation(BaseModel):
    """申样批量操作模型"""
    
    sample_ids: List[UUID] = Field(
        description="申样ID列表",
        min_items=1
    )
    operation: str = Field(
        description="操作类型",
        example="approve"  # approve, reject, ship, cancel
    )
    reason: Optional[str] = Field(
        None,
        description="操作理由",
        max_length=500,
        example="批量审核通过"
    )
    
    @validator('sample_ids')
    def validate_sample_ids(cls, v):
        """验证申样ID列表"""
        if not v:
            raise ValueError('申样ID列表不能为空')
        return v


class SampleApproval(BaseModel):
    """申样审核模型"""
    
    sample_id: UUID = Field(
        description="申样ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    approved: bool = Field(
        description="是否通过",
        example=True
    )
    reason: str = Field(
        description="审核理由",
        min_length=1,
        max_length=500,
        example="申请人资质符合要求，同意发放样品"
    )
    expires_days: Optional[int] = Field(
        30,
        description="有效期天数",
        gt=0,
        le=90,
        example=30
    )
    
    @validator('reason')
    def validate_reason(cls, v):
        """验证审核理由"""
        if not v or not v.strip():
            raise ValueError('审核理由不能为空')
        return v.strip()


class SampleShipping(BaseModel):
    """申样发货模型"""
    
    sample_id: UUID = Field(
        description="申样ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    tracking_number: str = Field(
        description="快递单号",
        min_length=1,
        example="SF1234567890"
    )
    shipping_company: str = Field(
        description="快递公司",
        min_length=1,
        example="顺丰速运"
    )
    
    @validator('tracking_number')
    def validate_tracking_number(cls, v):
        """验证快递单号"""
        if not v or not v.strip():
            raise ValueError('快递单号不能为空')
        return v.strip()
    
    @validator('shipping_company')
    def validate_shipping_company(cls, v):
        """验证快递公司"""
        if not v or not v.strip():
            raise ValueError('快递公司不能为空')
        return v.strip()