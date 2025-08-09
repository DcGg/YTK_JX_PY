"""API路由模块

定义所有API路由的入口点。

Author: 云推客严选开发团队
Date: 2024
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .products import router as products_router
from .orders import router as orders_router
from .collections import router as collections_router
from .samples import router as samples_router
from .relationships import router as relationships_router
from .health import router as health_router

# 创建主路由
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(health_router, prefix="/health", tags=["健康检查"])
api_router.include_router(auth_router, prefix="/auth", tags=["用户认证"])
api_router.include_router(products_router, prefix="/products", tags=["商品管理"])
api_router.include_router(orders_router, prefix="/orders", tags=["订单管理"])
api_router.include_router(collections_router, prefix="/collections", tags=["货盘管理"])
api_router.include_router(samples_router, prefix="/samples", tags=["申样管理"])
api_router.include_router(relationships_router, prefix="/relationships", tags=["关系管理"])

__all__ = ["api_router"]