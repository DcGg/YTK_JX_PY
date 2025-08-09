"""商品管理API

提供商品的CRUD操作、搜索、分类管理等API接口。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from ..core.security import (
    get_current_user_id, require_roles, require_active_user
)
from ..models.user import User, UserRole
from uuid import UUID
from ..models.product import (
    Product, ProductCreate, ProductUpdate, ProductResponse,
    ProductListResponse, ProductSearch, ProductStatistics,
    ProductStatus, ProductCategory
)
from ..models.common import (
    ResponseModel, SuccessResponse, ErrorResponse,
    PaginationParams
)
from ..services.product_service import get_product_service, ProductService

# 创建路由器
router = APIRouter(prefix="/products", tags=["商品管理"])


@router.post(
    "/",
    response_model=ResponseModel[Product],
    summary="创建商品",
    description="商家创建新商品"
)
async def create_product(
    product_data: ProductCreate,
    current_user_id = Depends(get_current_user_id),
    product_service: ProductService = Depends(get_product_service)
):
    """创建商品
    
    只有商家可以创建商品。
    """
    try:
        result = await product_service.create_product(
            product_data=product_data,
            merchant_id=current_user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建商品API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建商品失败"
        )


@router.get(
    "/{product_id}",
    response_model=ResponseModel[ProductResponse],
    summary="获取商品详情",
    description="根据ID获取商品详细信息"
)
async def get_product(
    product_id: str,
    include_merchant: bool = Query(False, description="是否包含商家信息"),
    product_service: ProductService = Depends(get_product_service)
):
    """获取商品详情
    
    任何人都可以查看商品详情。
    """
    try:
        result = await product_service.get_product_by_id(
            product_id=product_id,
            include_merchant=include_merchant
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商品详情API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商品详情失败"
        )


@router.put(
    "/{product_id}",
    response_model=ResponseModel[Product],
    summary="更新商品",
    description="商家更新自己的商品信息"
)
async def update_product(
    product_id: str,
    update_data: ProductUpdate,
    current_user_id = Depends(get_current_user_id),
    product_service: ProductService = Depends(get_product_service)
):
    """更新商品
    
    只有商品所属的商家可以更新商品。
    """
    try:
        result = await product_service.update_product(
            product_id=product_id,
            update_data=update_data,
            merchant_id=current_user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新商品API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新商品失败"
        )


@router.delete(
    "/{product_id}",
    response_model=ResponseModel[bool],
    summary="删除商品",
    description="商家删除自己的商品（软删除）"
)
async def delete_product(
    product_id: str,
    current_user_id = Depends(get_current_user_id),
    product_service: ProductService = Depends(get_product_service)
):
    """删除商品
    
    只有商品所属的商家可以删除商品。
    实际执行软删除，将状态设置为已删除。
    """
    try:
        result = await product_service.delete_product(
            product_id=product_id,
            merchant_id=current_user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除商品API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除商品失败"
        )


@router.get(
    "/",
    response_model=ResponseModel[ProductListResponse],
    summary="搜索商品",
    description="根据条件搜索商品列表"
)
async def search_products(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[ProductCategory] = Query(None, description="商品分类"),
    merchant_id: Optional[str] = Query(None, description="商家ID"),
    status: Optional[ProductStatus] = Query(None, description="商品状态"),
    min_price: Optional[float] = Query(None, description="最低价格"),
    max_price: Optional[float] = Query(None, description="最高价格"),
    tags: Optional[List[str]] = Query(None, description="标签列表"),
    is_featured: Optional[bool] = Query(None, description="是否精选"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    product_service: ProductService = Depends(get_product_service)
):
    """搜索商品
    
    支持多种搜索条件和排序方式。
    """
    try:
        # 构造搜索参数
        search_params = ProductSearch(
            keyword=keyword,
            category=category,
            merchant_id=merchant_id,
            status=status,
            min_price=min_price,
            max_price=max_price,
            tags=tags,
            is_featured=is_featured,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 构造分页参数
        pagination = PaginationParams(
            page=page,
            page_size=page_size
        )
        
        result = await product_service.search_products(
            search_params=search_params,
            pagination=pagination
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索商品API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索商品失败"
        )


@router.get(
    "/merchant/my",
    response_model=ResponseModel[ProductListResponse],
    summary="获取我的商品",
    description="商家获取自己的商品列表"
)
async def get_my_products(
    status: Optional[ProductStatus] = Query(None, description="商品状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user_id = Depends(get_current_user_id),
    product_service: ProductService = Depends(get_product_service)
):
    """获取我的商品
    
    商家获取自己的商品列表。
    """
    try:
        # 构造分页参数
        pagination = PaginationParams(
            page=page,
            page_size=page_size
        )
        
        result = await product_service.get_merchant_products(
            merchant_id=current_user_id,
            pagination=pagination,
            status=status
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取我的商品API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取我的商品失败"
        )


@router.get(
    "/merchant/{merchant_id}",
    response_model=ResponseModel[ProductListResponse],
    summary="获取商家商品",
    description="获取指定商家的商品列表"
)
async def get_merchant_products(
    merchant_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    product_service: ProductService = Depends(get_product_service)
):
    """获取商家商品
    
    获取指定商家的公开商品列表。
    """
    try:
        # 构造分页参数
        pagination = PaginationParams(
            page=page,
            page_size=page_size
        )
        
        result = await product_service.get_merchant_products(
            merchant_id=merchant_id,
            pagination=pagination,
            status=ProductStatus.ACTIVE  # 只显示上架的商品
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商家商品API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商家商品失败"
        )


@router.patch(
    "/{product_id}/stock",
    response_model=ResponseModel[Product],
    summary="更新商品库存",
    description="商家更新商品库存数量"
)
async def update_product_stock(
    product_id: str,
    quantity_change: int = Query(..., description="库存变化量（正数增加，负数减少）"),
    current_user_id = Depends(get_current_user_id),
    product_service: ProductService = Depends(get_product_service)
):
    """更新商品库存
    
    商家可以增加或减少商品库存。
    """
    try:
        result = await product_service.update_product_stock(
            product_id=product_id,
            quantity_change=quantity_change,
            merchant_id=current_user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新商品库存API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新商品库存失败"
        )


@router.get(
    "/statistics/overview",
    response_model=ResponseModel[ProductStatistics],
    summary="获取商品统计",
    description="获取商品统计信息"
)
async def get_product_statistics(
    current_user_id = Depends(get_current_user_id),
    product_service: ProductService = Depends(get_product_service)
):
    """获取商品统计
    
    商家获取自己的商品统计。
    """
    try:
        # 商家获取自己的商品统计
        result = await product_service.get_product_statistics(
            merchant_id=current_user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商品统计API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商品统计失败"
        )


@router.patch(
    "/batch/update",
    response_model=ResponseModel[List[Product]],
    summary="批量更新商品",
    description="商家批量更新商品信息"
)
async def batch_update_products(
    product_ids: List[str],
    status: Optional[ProductStatus] = None,
    is_featured: Optional[bool] = None,
    current_user_id = Depends(get_current_user_id),
    product_service: ProductService = Depends(get_product_service)
):
    """批量更新商品
    
    商家可以批量更新商品状态、是否精选等信息。
    """
    try:
        # 构造更新数据
        update_data = {}
        if status is not None:
            update_data["status"] = status.value
        if is_featured is not None:
            update_data["is_featured"] = is_featured
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供要更新的字段"
            )
        
        result = await product_service.batch_update_products(
            product_ids=product_ids,
            update_data=update_data,
            merchant_id=current_user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量更新商品API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量更新商品失败"
        )


@router.get(
    "/categories/list",
    response_model=ResponseModel[List[dict]],
    summary="获取商品分类列表",
    description="获取所有可用的商品分类"
)
async def get_product_categories():
    """获取商品分类列表
    
    返回所有可用的商品分类。
    """
    try:
        categories = [
            {
                "value": category.value,
                "label": category.value,
                "description": f"{category.value}类商品"
            }
            for category in ProductCategory
        ]
        
        return ResponseModel(
            success=True,
            message="获取商品分类成功",
            data=categories
        )
        
    except Exception as e:
        logger.error(f"获取商品分类API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商品分类失败"
        )