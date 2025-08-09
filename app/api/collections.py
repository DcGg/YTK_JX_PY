"""货盘管理API

提供货盘的CRUD操作、商品管理、搜索等功能的API接口。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from loguru import logger

from ..core.security import (
    get_current_user_id, require_roles, require_active_user
)
from ..models.user import User, UserRole
from ..models.collection import (
    Collection, CollectionCreate, CollectionUpdate, CollectionResponse,
    CollectionDetailResponse, CollectionListResponse, CollectionSearch,
    CollectionStatistics, CollectionStatus, CollectionType,
    CollectionItem, CollectionItemCreate, CollectionItemUpdate,
    CollectionItemResponse
)
from ..models.common import (
    ResponseModel, PaginationParams
)
from ..services.collection_service import get_collection_service

router = APIRouter(prefix="/collections", tags=["货盘管理"])


@router.post("/", response_model=ResponseModel[Collection])
async def create_collection(
    collection_data: CollectionCreate,
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """创建货盘
    
    只有商家和达人可以创建货盘。
    """
    # 权限检查：只有商家和达人可以创建货盘
    if current_user.role not in [UserRole.MERCHANT, UserRole.INFLUENCER, UserRole.LEADER]:
        raise HTTPException(
            status_code=403,
            detail="只有商家和达人可以创建货盘"
        )
    
    result = await collection_service.create_collection(
        collection_data=collection_data,
        creator_id=current_user.id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get("/{collection_id}", response_model=ResponseModel[CollectionDetailResponse])
async def get_collection(
    collection_id: str = Path(..., description="货盘ID"),
    include_items: bool = Query(True, description="是否包含货盘商品"),
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """获取货盘详情
    
    公开货盘所有人可查看，私有货盘只有创建者可查看。
    """
    result = await collection_service.get_collection_by_id(
        collection_id=collection_id,
        user_id=current_user.id if current_user else None,
        include_items=include_items
    )
    
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)
    
    return result


@router.put("/{collection_id}", response_model=ResponseModel[Collection])
async def update_collection(
    collection_id: str = Path(..., description="货盘ID"),
    update_data: CollectionUpdate = ...,
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """更新货盘信息
    
    只有货盘创建者可以更新。
    """
    result = await collection_service.update_collection(
        collection_id=collection_id,
        update_data=update_data,
        user_id=current_user.id
    )
    
    if not result.success:
        if "不存在" in result.message:
            raise HTTPException(status_code=404, detail=result.message)
        elif "无权限" in result.message:
            raise HTTPException(status_code=403, detail=result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.delete("/{collection_id}", response_model=ResponseModel[bool])
async def delete_collection(
    collection_id: str = Path(..., description="货盘ID"),
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """删除货盘
    
    只有货盘创建者可以删除。执行软删除。
    """
    result = await collection_service.delete_collection(
        collection_id=collection_id,
        user_id=current_user.id
    )
    
    if not result.success:
        if "不存在" in result.message:
            raise HTTPException(status_code=404, detail=result.message)
        elif "无权限" in result.message:
            raise HTTPException(status_code=403, detail=result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.post("/{collection_id}/items", response_model=ResponseModel[CollectionItem])
async def add_item_to_collection(
    collection_id: str = Path(..., description="货盘ID"),
    item_data: CollectionItemCreate = ...,
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """向货盘添加商品
    
    只有货盘创建者可以添加商品。
    """
    result = await collection_service.add_item_to_collection(
        collection_id=collection_id,
        item_data=item_data,
        user_id=current_user.id
    )
    
    if not result.success:
        if "不存在" in result.message:
            raise HTTPException(status_code=404, detail=result.message)
        elif "无权限" in result.message:
            raise HTTPException(status_code=403, detail=result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.delete("/{collection_id}/items/{item_id}", response_model=ResponseModel[bool])
async def remove_item_from_collection(
    collection_id: str = Path(..., description="货盘ID"),
    item_id: str = Path(..., description="商品项ID"),
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """从货盘移除商品
    
    只有货盘创建者可以移除商品。
    """
    result = await collection_service.remove_item_from_collection(
        collection_id=collection_id,
        item_id=item_id,
        user_id=current_user.id
    )
    
    if not result.success:
        if "不存在" in result.message:
            raise HTTPException(status_code=404, detail=result.message)
        elif "无权限" in result.message:
            raise HTTPException(status_code=403, detail=result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get("/", response_model=ResponseModel[CollectionListResponse])
async def search_collections(
    # 搜索参数
    name: Optional[str] = Query(None, description="货盘名称"),
    creator_id: Optional[str] = Query(None, description="创建者ID"),
    type: Optional[CollectionType] = Query(None, description="货盘类型"),
    status: Optional[CollectionStatus] = Query(None, description="货盘状态"),
    tags: Optional[List[str]] = Query(None, description="标签列表"),
    sort_by: Optional[str] = Query("updated_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    
    # 分页参数
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """搜索货盘
    
    支持按名称、创建者、类型、状态、标签等条件搜索。
    公开货盘所有人可查看，私有货盘只有创建者可查看。
    """
    search_params = CollectionSearch(
        name=name,
        creator_id=creator_id,
        type=type,
        status=status,
        tags=tags,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    pagination = PaginationParams(
        page=page,
        page_size=page_size
    )
    
    result = await collection_service.search_collections(
        search_params=search_params,
        pagination=pagination,
        user_id=current_user.id if current_user else None
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get("/my/collections", response_model=ResponseModel[CollectionListResponse])
async def get_my_collections(
    # 搜索参数
    name: Optional[str] = Query(None, description="货盘名称"),
    type: Optional[CollectionType] = Query(None, description="货盘类型"),
    status: Optional[CollectionStatus] = Query(None, description="货盘状态"),
    sort_by: Optional[str] = Query("updated_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    
    # 分页参数
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """获取我的货盘列表
    
    获取当前用户创建的所有货盘。
    """
    search_params = CollectionSearch(
        name=name,
        creator_id=current_user.id,  # 只查看自己的货盘
        type=type,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    pagination = PaginationParams(
        page=page,
        page_size=page_size
    )
    
    result = await collection_service.search_collections(
        search_params=search_params,
        pagination=pagination,
        user_id=current_user.id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get("/statistics", response_model=ResponseModel[CollectionStatistics])
async def get_collection_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(require_active_user),
    collection_service = Depends(get_collection_service)
):
    """获取货盘统计信息
    
    获取当前用户的货盘统计数据。
    """
    result = await collection_service.get_collection_statistics(
        user_id=current_user.id,
        days=days
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get("/types", response_model=ResponseModel[List[dict]])
async def get_collection_types():
    """获取货盘类型列表
    
    返回所有可用的货盘类型。
    """
    types = [
        {"value": type_item.value, "label": type_item.value}
        for type_item in CollectionType
    ]
    
    return ResponseModel(
        success=True,
        message="获取货盘类型成功",
        data=types
    )


@router.get("/statuses", response_model=ResponseModel[List[dict]])
async def get_collection_statuses():
    """获取货盘状态列表
    
    返回所有可用的货盘状态。
    """
    statuses = [
        {"value": status_item.value, "label": status_item.value}
        for status_item in CollectionStatus
        if status_item != CollectionStatus.DELETED  # 不显示已删除状态
    ]
    
    return ResponseModel(
        success=True,
        message="获取货盘状态成功",
        data=statuses
    )