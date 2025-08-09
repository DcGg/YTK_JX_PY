"""服务层模块初始化

定义业务逻辑服务层，包括用户服务、商品服务、订单服务等。

Author: 云推客严选开发团队
Date: 2024
"""

from .auth_service import AuthService
from .product_service import ProductService
from .order_service import OrderService
from .collection_service import CollectionService
from .sample_service import SampleService
from .relationship_service import RelationshipService
from .wechat_service import WeChatService

__all__ = [
    "AuthService",
    "ProductService",
    "OrderService",
    "CollectionService",
    "SampleService",
    "RelationshipService",
    "WeChatService",
]