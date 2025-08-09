"""货盘数据模型

定义货盘相关的数据模型，包括货盘信息、商品管理、统计分析等。

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


class CollectionStatus(str, Enum):
    """货盘状态枚举"""
    
    DRAFT = "draft"          # 草稿
    ACTIVE = "active"        # 活跃
    INACTIVE = "inactive"    # 停用
    ARCHIVED = "archived"    # 已归档


class CollectionType(str, Enum):
    """货盘类型枚举"""
    
    GENERAL = "general"      # 通用货盘
    SEASONAL = "seasonal"    # 季节性货盘
    PROMOTIONAL = "promotional"  # 促销货盘
    CATEGORY = "category"    # 分类货盘
    BRAND = "brand"          # 品牌货盘
    CUSTOM = "custom"        # 自定义货盘


class CollectionItemBase(BaseModel):
    """货盘商品基础模型"""
    
    product_id: UUID = Field(
        description="商品ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    sort_order: int = Field(
        0,
        description="排序顺序",
        example=1
    )
    featured: bool = Field(
        False,
        description="是否推荐",
        example=True
    )
    custom_price: Optional[Decimal] = Field(
        None,
        description="自定义价格",
        gt=0,
        decimal_places=2,
        example=199.00
    )
    custom_commission_rate: Optional[Decimal] = Field(
        None,
        description="自定义佣金比例",
        ge=0,
        le=1,
        decimal_places=4,
        example=0.20
    )
    remark: Optional[str] = Field(
        None,
        description="备注",
        max_length=500,
        example="重点推荐商品"
    )


class CollectionItemCreate(CollectionItemBase):
    """创建货盘商品模型"""
    pass


class CollectionItemUpdate(BaseModel):
    """更新货盘商品模型"""
    
    sort_order: Optional[int] = Field(
        None,
        description="排序顺序"
    )
    featured: Optional[bool] = Field(
        None,
        description="是否推荐"
    )
    custom_price: Optional[Decimal] = Field(
        None,
        description="自定义价格",
        gt=0,
        decimal_places=2
    )
    custom_commission_rate: Optional[Decimal] = Field(
        None,
        description="自定义佣金比例",
        ge=0,
        le=1,
        decimal_places=4
    )
    remark: Optional[str] = Field(
        None,
        description="备注",
        max_length=500
    )


class CollectionItem(UUIDMixin, CollectionItemBase, TimestampMixin):
    """货盘商品完整模型"""
    
    collection_id: UUID = Field(
        description="货盘ID",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    
    class Config:
        """Pydantic配置"""
        from_attributes = True


class CollectionItemResponse(CollectionItem):
    """货盘商品响应模型
    
    包含商品详细信息。
    """
    
    product_title: Optional[str] = Field(
        None,
        description="商品标题",
        example="高端护肤精华液 50ml"
    )
    product_image: Optional[str] = Field(
        None,
        description="商品主图",
        example="https://example.com/product/image.jpg"
    )
    product_price: Optional[Decimal] = Field(
        None,
        description="商品原价",
        example=299.00
    )
    product_sale_price: Optional[Decimal] = Field(
        None,
        description="商品售价",
        example=199.00
    )
    product_commission_rate: Optional[Decimal] = Field(
        None,
        description="商品佣金比例",
        example=0.15
    )
    product_stock: Optional[int] = Field(
        None,
        description="商品库存",
        example=100
    )
    product_status: Optional[str] = Field(
        None,
        description="商品状态",
        example="active"
    )
    sales_count: Optional[int] = Field(
        0,
        description="销售数量",
        example=50
    )
    commission_earned: Optional[Decimal] = Field(
        0,
        description="已赚佣金",
        example=1500.00
    )
    
    # 计算字段
    effective_price: Optional[Decimal] = Field(
        None,
        description="有效价格（自定义价格或商品售价）",
        example=199.00
    )
    effective_commission_rate: Optional[Decimal] = Field(
        None,
        description="有效佣金比例",
        example=0.20
    )
    commission_amount: Optional[Decimal] = Field(
        None,
        description="佣金金额",
        example=39.80
    )


class CollectionBase(BaseModel):
    """货盘基础模型"""
    
    owner_id: UUID = Field(
        description="货盘所有者ID（团长或达人）",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    title: str = Field(
        description="货盘标题",
        min_length=1,
        max_length=100,
        example="精选美妆货盘"
    )
    description: Optional[str] = Field(
        None,
        description="货盘描述",
        max_length=1000,
        example="精心挑选的优质美妆产品，品质保证，价格优惠"
    )
    cover_image: Optional[str] = Field(
        None,
        description="封面图片",
        example="https://example.com/collection/cover.jpg"
    )
    collection_type: CollectionType = Field(
        CollectionType.GENERAL,
        description="货盘类型"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="标签列表",
        example=["美妆", "护肤", "精选"]
    )
    is_public: bool = Field(
        True,
        description="是否公开",
        example=True
    )
    is_featured: bool = Field(
        False,
        description="是否推荐",
        example=False
    )
    status: CollectionStatus = Field(
        CollectionStatus.DRAFT,
        description="货盘状态"
    )
    
    @validator('title')
    def validate_title(cls, v):
        """验证货盘标题"""
        if not v or not v.strip():
            raise ValueError('货盘标题不能为空')
        return v.strip()


class CollectionCreate(CollectionBase):
    """创建货盘模型"""
    pass


class CollectionUpdate(BaseModel):
    """更新货盘模型"""
    
    title: Optional[str] = Field(
        None,
        description="货盘标题",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        description="货盘描述",
        max_length=1000
    )
    cover_image: Optional[str] = Field(
        None,
        description="封面图片"
    )
    collection_type: Optional[CollectionType] = Field(
        None,
        description="货盘类型"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="标签列表"
    )
    is_public: Optional[bool] = Field(
        None,
        description="是否公开"
    )
    is_featured: Optional[bool] = Field(
        None,
        description="是否推荐"
    )
    status: Optional[CollectionStatus] = Field(
        None,
        description="货盘状态"
    )
    
    @validator('title')
    def validate_title(cls, v):
        """验证货盘标题"""
        if v is not None and (not v or not v.strip()):
            raise ValueError('货盘标题不能为空')
        return v.strip() if v else v


class Collection(UUIDMixin, CollectionBase, TimestampMixin):
    """货盘完整模型"""
    
    view_count: int = Field(
        0,
        description="浏览次数",
        example=1500
    )
    share_count: int = Field(
        0,
        description="分享次数",
        example=50
    )
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "owner_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "精选美妆货盘",
                "description": "精心挑选的优质美妆产品",
                "collection_type": "category",
                "is_public": True,
                "status": "active",
                "view_count": 1500,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class CollectionResponse(Collection):
    """货盘响应模型
    
    用于API响应，包含额外的计算字段。
    """
    
    owner_name: Optional[str] = Field(
        None,
        description="所有者姓名",
        example="张三"
    )
    owner_type: Optional[str] = Field(
        None,
        description="所有者类型",
        example="leader"
    )
    product_count: int = Field(
        0,
        description="商品数量",
        example=25
    )
    total_sales: int = Field(
        0,
        description="总销量",
        example=500
    )
    total_commission: Decimal = Field(
        0,
        description="总佣金",
        example=7500.00
    )
    average_price: Optional[Decimal] = Field(
        None,
        description="平均价格",
        example=199.99
    )
    conversion_rate: Optional[float] = Field(
        None,
        description="转化率",
        example=0.15
    )
    last_updated: Optional[datetime] = Field(
        None,
        description="最后更新时间"
    )


class CollectionDetailResponse(CollectionResponse):
    """货盘详情响应模型
    
    包含商品列表。
    """
    
    items: List[CollectionItemResponse] = Field(
        default_factory=list,
        description="商品列表"
    )


class CollectionListResponse(BaseModel):
    """货盘列表响应模型"""
    
    collections: List[CollectionResponse] = Field(
        description="货盘列表"
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


class CollectionSearch(BaseModel):
    """货盘搜索模型"""
    
    keyword: Optional[str] = Field(
        None,
        description="搜索关键词",
        example="美妆"
    )
    owner_id: Optional[UUID] = Field(
        None,
        description="所有者ID"
    )
    collection_type: Optional[CollectionType] = Field(
        None,
        description="货盘类型"
    )
    status: Optional[CollectionStatus] = Field(
        None,
        description="货盘状态"
    )
    is_public: Optional[bool] = Field(
        None,
        description="是否公开"
    )
    is_featured: Optional[bool] = Field(
        None,
        description="是否推荐"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="标签列表"
    )
    min_product_count: Optional[int] = Field(
        None,
        description="最少商品数量",
        ge=0
    )
    max_product_count: Optional[int] = Field(
        None,
        description="最多商品数量",
        ge=0
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="排序字段",
        example="view_count"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="排序方向",
        example="desc"
    )


class CollectionStatistics(BaseModel):
    """货盘统计模型"""
    
    total_collections: int = Field(
        description="货盘总数",
        example=100
    )
    active_collections: int = Field(
        description="活跃货盘数",
        example=80
    )
    public_collections: int = Field(
        description="公开货盘数",
        example=70
    )
    featured_collections: int = Field(
        description="推荐货盘数",
        example=10
    )
    total_products: int = Field(
        description="总商品数",
        example=2500
    )
    total_views: int = Field(
        description="总浏览量",
        example=150000
    )
    total_shares: int = Field(
        description="总分享量",
        example=5000
    )
    total_sales: int = Field(
        description="总销量",
        example=10000
    )
    total_commission: Decimal = Field(
        description="总佣金",
        example=150000.00
    )
    average_products_per_collection: float = Field(
        description="平均每个货盘商品数",
        example=25.0
    )
    top_collections: List[Dict[str, Any]] = Field(
        description="热门货盘",
        example=[
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "精选美妆货盘",
                "view_count": 5000,
                "sales_count": 200
            }
        ]
    )
    collection_types_distribution: List[Dict[str, Any]] = Field(
        description="货盘类型分布",
        example=[
            {"type": "general", "count": 40},
            {"type": "category", "count": 30},
            {"type": "promotional", "count": 20}
        ]
    )


class CollectionBatchOperation(BaseModel):
    """货盘批量操作模型"""
    
    collection_ids: List[UUID] = Field(
        description="货盘ID列表",
        min_items=1
    )
    operation: str = Field(
        description="操作类型",
        example="activate"  # activate, deactivate, delete, feature, unfeature
    )
    
    @validator('collection_ids')
    def validate_collection_ids(cls, v):
        """验证货盘ID列表"""
        if not v:
            raise ValueError('货盘ID列表不能为空')
        return v


class CollectionShareRequest(BaseModel):
    """货盘分享请求模型"""
    
    collection_id: UUID = Field(
        description="货盘ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    platform: str = Field(
        description="分享平台",
        example="wechat"  # wechat, weibo, douyin, etc.
    )
    custom_message: Optional[str] = Field(
        None,
        description="自定义分享文案",
        max_length=500,
        example="推荐这个超棒的美妆货盘！"
    )


class CollectionShareResponse(BaseModel):
    """货盘分享响应模型"""
    
    share_url: str = Field(
        description="分享链接",
        example="https://example.com/collection/share/123e4567-e89b-12d3-a456-426614174000"
    )
    qr_code: Optional[str] = Field(
        None,
        description="分享二维码",
        example="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    )
    share_text: str = Field(
        description="分享文案",
        example="精选美妆货盘，品质保证，快来看看吧！"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="过期时间"
    )