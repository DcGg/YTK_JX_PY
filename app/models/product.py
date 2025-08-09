"""商品数据模型

定义商品相关的数据模型，包括商品信息、分类、价格、库存等。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from decimal import Decimal
from pydantic import Field, validator
from uuid import UUID

from .common import BaseModel, TimestampMixin, UUIDMixin


class ProductStatus(str, Enum):
    """商品状态枚举"""
    
    DRAFT = "draft"          # 草稿
    ACTIVE = "active"        # 上架
    INACTIVE = "inactive"    # 下架
    OUT_OF_STOCK = "out_of_stock"  # 缺货
    DISCONTINUED = "discontinued"  # 停产


class ProductCategory(str, Enum):
    """商品分类枚举"""
    
    BEAUTY = "beauty"        # 美妆护肤
    FASHION = "fashion"      # 服装配饰
    FOOD = "food"            # 食品饮料
    HOME = "home"            # 家居用品
    ELECTRONICS = "electronics"  # 数码电器
    HEALTH = "health"        # 健康保健
    BABY = "baby"            # 母婴用品
    SPORTS = "sports"        # 运动户外
    BOOKS = "books"          # 图书文娱
    OTHER = "other"          # 其他


class ProductImage(BaseModel):
    """商品图片模型"""
    
    url: str = Field(
        description="图片URL",
        example="https://example.com/product/image1.jpg"
    )
    alt_text: Optional[str] = Field(
        None,
        description="图片描述",
        example="商品主图"
    )
    sort_order: int = Field(
        0,
        description="排序顺序",
        example=1
    )
    is_primary: bool = Field(
        False,
        description="是否为主图",
        example=True
    )


class ProductSpec(BaseModel):
    """商品规格模型"""
    
    name: str = Field(
        description="规格名称",
        example="颜色"
    )
    value: str = Field(
        description="规格值",
        example="红色"
    )
    price_adjustment: Optional[Decimal] = Field(
        None,
        description="价格调整",
        example=10.00
    )
    stock: Optional[int] = Field(
        None,
        description="库存数量",
        example=100
    )


class ProductBase(BaseModel):
    """商品基础模型"""
    
    merchant_id: UUID = Field(
        description="商家ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    title: str = Field(
        description="商品标题",
        min_length=1,
        max_length=200,
        example="高端护肤精华液 50ml"
    )
    description: Optional[str] = Field(
        None,
        description="商品描述",
        max_length=5000,
        example="采用天然植物精华，深层滋养肌肤，改善肌肤质地"
    )
    category: ProductCategory = Field(
        description="商品分类",
        example=ProductCategory.BEAUTY
    )
    brand: Optional[str] = Field(
        None,
        description="品牌名称",
        max_length=100,
        example="兰蔻"
    )
    model: Optional[str] = Field(
        None,
        description="型号规格",
        max_length=100,
        example="LAN-001"
    )
    original_price: Decimal = Field(
        description="原价",
        gt=0,
        decimal_places=2,
        example=299.00
    )
    sale_price: Decimal = Field(
        description="售价",
        gt=0,
        decimal_places=2,
        example=199.00
    )
    commission_rate: Decimal = Field(
        description="佣金比例",
        ge=0,
        le=1,
        decimal_places=4,
        example=0.15
    )
    stock: int = Field(
        description="库存数量",
        ge=0,
        example=100
    )
    min_order_quantity: int = Field(
        1,
        description="最小起订量",
        ge=1,
        example=1
    )
    max_order_quantity: Optional[int] = Field(
        None,
        description="最大订购量",
        example=10
    )
    weight: Optional[Decimal] = Field(
        None,
        description="重量（克）",
        ge=0,
        decimal_places=2,
        example=50.00
    )
    dimensions: Optional[Dict[str, Decimal]] = Field(
        None,
        description="尺寸（长宽高，单位：厘米）",
        example={"length": 10.5, "width": 5.2, "height": 15.8}
    )
    images: List[ProductImage] = Field(
        default_factory=list,
        description="商品图片列表"
    )
    specifications: List[ProductSpec] = Field(
        default_factory=list,
        description="商品规格列表"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="商品标签",
        example=["护肤", "精华", "抗衰老"]
    )
    status: ProductStatus = Field(
        ProductStatus.DRAFT,
        description="商品状态"
    )
    featured: bool = Field(
        False,
        description="是否推荐",
        example=False
    )
    video_url: Optional[str] = Field(
        None,
        description="商品视频URL",
        example="https://example.com/product/video.mp4"
    )
    
    @validator('sale_price')
    def validate_sale_price(cls, v, values):
        """验证售价不能高于原价"""
        if 'original_price' in values and v > values['original_price']:
            raise ValueError('售价不能高于原价')
        return v
    
    @validator('max_order_quantity')
    def validate_max_order_quantity(cls, v, values):
        """验证最大订购量不能小于最小起订量"""
        if v is not None and 'min_order_quantity' in values and v < values['min_order_quantity']:
            raise ValueError('最大订购量不能小于最小起订量')
        return v
    
    @validator('images')
    def validate_images(cls, v):
        """验证至少有一张主图"""
        if v:
            primary_count = sum(1 for img in v if img.is_primary)
            if primary_count == 0:
                # 如果没有设置主图，将第一张设为主图
                v[0].is_primary = True
            elif primary_count > 1:
                raise ValueError('只能有一张主图')
        return v


class ProductCreate(ProductBase):
    """创建商品模型"""
    
    @validator('title')
    def validate_title(cls, v):
        """验证商品标题"""
        if not v or not v.strip():
            raise ValueError('商品标题不能为空')
        return v.strip()


class ProductUpdate(BaseModel):
    """更新商品模型"""
    
    title: Optional[str] = Field(
        None,
        description="商品标题",
        min_length=1,
        max_length=200
    )
    description: Optional[str] = Field(
        None,
        description="商品描述",
        max_length=5000
    )
    category: Optional[ProductCategory] = Field(
        None,
        description="商品分类"
    )
    brand: Optional[str] = Field(
        None,
        description="品牌名称",
        max_length=100
    )
    model: Optional[str] = Field(
        None,
        description="型号规格",
        max_length=100
    )
    original_price: Optional[Decimal] = Field(
        None,
        description="原价",
        gt=0,
        decimal_places=2
    )
    sale_price: Optional[Decimal] = Field(
        None,
        description="售价",
        gt=0,
        decimal_places=2
    )
    commission_rate: Optional[Decimal] = Field(
        None,
        description="佣金比例",
        ge=0,
        le=1,
        decimal_places=4
    )
    stock: Optional[int] = Field(
        None,
        description="库存数量",
        ge=0
    )
    min_order_quantity: Optional[int] = Field(
        None,
        description="最小起订量",
        ge=1
    )
    max_order_quantity: Optional[int] = Field(
        None,
        description="最大订购量"
    )
    weight: Optional[Decimal] = Field(
        None,
        description="重量（克）",
        ge=0,
        decimal_places=2
    )
    dimensions: Optional[Dict[str, Decimal]] = Field(
        None,
        description="尺寸（长宽高，单位：厘米）"
    )
    images: Optional[List[ProductImage]] = Field(
        None,
        description="商品图片列表"
    )
    specifications: Optional[List[ProductSpec]] = Field(
        None,
        description="商品规格列表"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="商品标签"
    )
    status: Optional[ProductStatus] = Field(
        None,
        description="商品状态"
    )
    featured: Optional[bool] = Field(
        None,
        description="是否推荐"
    )
    video_url: Optional[str] = Field(
        None,
        description="商品视频URL"
    )


class Product(UUIDMixin, ProductBase, TimestampMixin):
    """商品完整模型"""
    
    view_count: int = Field(
        0,
        description="浏览次数",
        example=1500
    )
    sales_count: int = Field(
        0,
        description="销售数量",
        example=50
    )
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "merchant_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "高端护肤精华液 50ml",
                "description": "采用天然植物精华，深层滋养肌肤",
                "category": "beauty",
                "brand": "兰蔻",
                "original_price": 299.00,
                "sale_price": 199.00,
                "commission_rate": 0.15,
                "stock": 100,
                "status": "active",
                "view_count": 1500,
                "sales_count": 50,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class ProductResponse(Product):
    """商品响应模型
    
    用于API响应，包含额外的计算字段。
    """
    
    merchant_name: Optional[str] = Field(
        None,
        description="商家名称",
        example="云推客科技"
    )
    discount_percentage: Optional[float] = Field(
        None,
        description="折扣百分比",
        example=33.44
    )
    commission_amount: Optional[Decimal] = Field(
        None,
        description="佣金金额",
        example=29.85
    )
    is_in_stock: bool = Field(
        True,
        description="是否有库存",
        example=True
    )
    rating: Optional[float] = Field(
        None,
        description="评分",
        example=4.5
    )
    review_count: Optional[int] = Field(
        None,
        description="评价数量",
        example=25
    )


class ProductListResponse(BaseModel):
    """商品列表响应模型"""
    
    products: List[ProductResponse] = Field(
        description="商品列表"
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


class ProductSearch(BaseModel):
    """商品搜索模型"""
    
    keyword: Optional[str] = Field(
        None,
        description="搜索关键词",
        example="护肤精华"
    )
    category: Optional[ProductCategory] = Field(
        None,
        description="商品分类"
    )
    brand: Optional[str] = Field(
        None,
        description="品牌名称",
        example="兰蔻"
    )
    min_price: Optional[Decimal] = Field(
        None,
        description="最低价格",
        ge=0,
        example=100.00
    )
    max_price: Optional[Decimal] = Field(
        None,
        description="最高价格",
        ge=0,
        example=500.00
    )
    status: Optional[ProductStatus] = Field(
        None,
        description="商品状态"
    )
    featured: Optional[bool] = Field(
        None,
        description="是否推荐"
    )
    merchant_id: Optional[UUID] = Field(
        None,
        description="商家ID"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="标签列表"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="排序字段",
        example="sale_price"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="排序方向",
        example="asc"
    )


class ProductStatistics(BaseModel):
    """商品统计模型"""
    
    total_products: int = Field(
        description="商品总数",
        example=1000
    )
    active_products: int = Field(
        description="上架商品数",
        example=800
    )
    out_of_stock: int = Field(
        description="缺货商品数",
        example=50
    )
    total_views: int = Field(
        description="总浏览量",
        example=50000
    )
    total_sales: int = Field(
        description="总销量",
        example=2000
    )
    average_price: Decimal = Field(
        description="平均价格",
        example=199.99
    )
    top_categories: List[Dict[str, Any]] = Field(
        description="热门分类",
        example=[
            {"category": "beauty", "count": 300},
            {"category": "fashion", "count": 250}
        ]
    )
    top_brands: List[Dict[str, Any]] = Field(
        description="热门品牌",
        example=[
            {"brand": "兰蔻", "count": 50},
            {"brand": "雅诗兰黛", "count": 45}
        ]
    )