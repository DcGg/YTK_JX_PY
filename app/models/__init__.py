"""数据模型模块

本模块包含云推客严选平台的所有数据模型定义，使用Pydantic进行数据验证和序列化。

模块结构：
- user: 用户相关模型（商家、团长、达人）
- product: 商品相关模型
- order: 订单相关模型
- collection: 货盘相关模型
- sample: 申样相关模型
- relationship: 用户关系模型
- common: 通用模型和基础类

Author: 云推客严选开发团队
Date: 2024
"""

from .user import (
    User,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserRole,
    UserProfile
)

from .product import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductStatus,
    ProductCategory
)

from .order import (
    Order,
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderItem,
    OrderItemCreate,
    OrderStatus,
    OrderStatistics
)

from .collection import (
    Collection,
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionItem,
    CollectionItemCreate,
    CollectionStatus
)

from .sample import (
    Sample,
    SampleCreate,
    SampleUpdate,
    SampleResponse,
    SampleStatus
)

from .relationship import (
    UserRelationship,
    RelationshipCreate,
    RelationshipUpdate,
    RelationshipResponse,
    RelationshipStatus
)

from .common import (
    BaseModel,
    PaginationParams,
    PaginationResponse,
    ResponseModel,
    ErrorResponse,
    SuccessResponse
)

__all__ = [
    # User models
    "User",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserRole",
    "UserProfile",
    
    # Product models
    "Product",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductStatus",
    "ProductCategory",
    
    # Order models
    "Order",
    "OrderCreate",
    "OrderUpdate",
    "OrderResponse",
    "OrderItem",
    "OrderItemCreate",
    "OrderStatus",
    "OrderStatistics",
    
    # Collection models
    "Collection",
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionItem",
    "CollectionItemCreate",
    "CollectionStatus",
    
    # Sample models
    "Sample",
    "SampleCreate",
    "SampleUpdate",
    "SampleResponse",
    "SampleStatus",
    
    # Relationship models
    "UserRelationship",
    "RelationshipCreate",
    "RelationshipUpdate",
    "RelationshipResponse",
    "RelationshipStatus",
    
    # Common models
    "BaseModel",
    "PaginationParams",
    "PaginationResponse",
    "ResponseModel",
    "ErrorResponse",
    "SuccessResponse"
]