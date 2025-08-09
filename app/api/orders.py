"""订单管理API

提供订单的CRUD操作、状态更新、搜索等功能。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import HTTPBearer

from ..core.security import (
    get_current_user_id, require_roles, require_active_user
)
from ..models.user import User, UserRole
from ..models.order import (
    Order, OrderCreate, OrderUpdate, OrderResponse,
    OrderListResponse, OrderSearch, OrderStatistics,
    OrderStatus, PaymentMethod, PaymentStatus
)
from ..models.common import (
    ResponseModel, PaginationParams, SuccessResponse
)
from ..services.order_service import get_order_service

# 创建路由器
router = APIRouter(prefix="/orders", tags=["订单管理"])
security = HTTPBearer()


@router.post(
    "/",
    response_model=ResponseModel[Order],
    summary="创建订单",
    description="创建新订单，支持多商品订单"
)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """创建订单
    
    - **order_data**: 订单创建数据
    - 只有激活用户可以创建订单
    - 自动验证商品库存和价格
    - 支持多商品订单
    """
    # 检查用户角色权限
    if current_user.role not in [UserRole.INFLUENCER, UserRole.LEADER]:
        raise HTTPException(
            status_code=403,
            detail="只有达人和团长可以创建订单"
        )
    
    result = await order_service.create_order(
        order_data=order_data,
        buyer_id=current_user.id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get(
    "/{order_id}",
    response_model=ResponseModel[OrderResponse],
    summary="获取订单详情",
    description="根据订单ID获取订单详细信息"
)
async def get_order(
    order_id: str = Path(..., description="订单ID"),
    include_items: bool = Query(True, description="是否包含订单项"),
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """获取订单详情
    
    - **order_id**: 订单ID
    - **include_items**: 是否包含订单项详情
    - 只能查看自己相关的订单（买家或卖家）
    """
    result = await order_service.get_order_by_id(
        order_id=order_id,
        user_id=current_user.id,
        include_items=include_items
    )
    
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)
    
    return result


@router.put(
    "/{order_id}/status",
    response_model=ResponseModel[Order],
    summary="更新订单状态",
    description="更新订单状态，支持订单流程管理"
)
async def update_order_status(
    order_id: str = Path(..., description="订单ID"),
    new_status: OrderStatus = Query(..., description="新状态"),
    notes: Optional[str] = Query(None, description="备注信息"),
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """更新订单状态
    
    - **order_id**: 订单ID
    - **new_status**: 新的订单状态
    - **notes**: 状态更新备注
    - 只有订单相关方（买家/卖家）可以更新状态
    - 状态转换需要符合业务规则
    """
    result = await order_service.update_order_status(
        order_id=order_id,
        new_status=new_status,
        user_id=current_user.id,
        notes=notes
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get(
    "/",
    response_model=ResponseModel[OrderListResponse],
    summary="搜索订单",
    description="根据条件搜索订单列表"
)
async def search_orders(
    # 分页参数
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    
    # 搜索条件
    order_number: Optional[str] = Query(None, description="订单号"),
    status: Optional[OrderStatus] = Query(None, description="订单状态"),
    payment_status: Optional[PaymentStatus] = Query(None, description="支付状态"),
    buyer_id: Optional[str] = Query(None, description="买家ID"),
    merchant_id: Optional[str] = Query(None, description="商家ID"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(None, ge=0, description="最小金额"),
    max_amount: Optional[float] = Query(None, ge=0, description="最大金额"),
    
    # 排序参数
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """搜索订单
    
    - 支持多种搜索条件组合
    - 支持分页和排序
    - 用户只能搜索自己相关的订单
    - 商家可以查看自己的销售订单
    - 达人/团长可以查看自己的采购订单
    """
    from datetime import datetime
    
    # 构造搜索参数
    search_params = OrderSearch(
        order_number=order_number,
        status=status,
        payment_status=payment_status,
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        min_amount=min_amount,
        max_amount=max_amount,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    pagination = PaginationParams(page=page, page_size=page_size)
    
    result = await order_service.search_orders(
        search_params=search_params,
        pagination=pagination,
        user_id=current_user_id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get(
    "/my/buyer",
    response_model=ResponseModel[OrderListResponse],
    summary="获取我的采购订单",
    description="获取当前用户作为买家的订单列表"
)
async def get_my_buyer_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[OrderStatus] = Query(None, description="订单状态"),
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """获取我的采购订单
    
    - 获取当前用户作为买家的所有订单
    - 支持按状态过滤
    - 按创建时间倒序排列
    """
    search_params = OrderSearch(
        buyer_id=current_user.id,
        status=status,
        sort_by="created_at",
        sort_order="desc"
    )
    
    pagination = PaginationParams(page=page, page_size=page_size)
    
    result = await order_service.search_orders(
        search_params=search_params,
        pagination=pagination,
        user_id=current_user.id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get(
    "/my/merchant",
    response_model=ResponseModel[OrderListResponse],
    summary="获取我的销售订单",
    description="获取当前用户作为商家的订单列表"
)
async def get_my_merchant_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[OrderStatus] = Query(None, description="订单状态"),
    current_user_id = Depends(get_current_user_id),
    order_service = Depends(get_order_service)
):
    """获取我的销售订单
    
    - 获取当前商家的所有销售订单
    - 支持按状态过滤
    - 按创建时间倒序排列
    - 只有商家可以访问
    """
    search_params = OrderSearch(
        merchant_id=current_user_id,
        status=status,
        sort_by="created_at",
        sort_order="desc"
    )
    
    pagination = PaginationParams(page=page, page_size=page_size)
    
    result = await order_service.search_orders(
        search_params=search_params,
        pagination=pagination,
        user_id=current_user.id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get(
    "/statistics",
    response_model=ResponseModel[OrderStatistics],
    summary="获取订单统计",
    description="获取用户的订单统计信息"
)
async def get_order_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """获取订单统计
    
    - **days**: 统计天数（1-365天）
    - 返回指定时间范围内的订单统计信息
    - 包括订单数量、金额、状态分布等
    """
    result = await order_service.get_order_statistics(
        user_id=current_user.id,
        days=days
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.put(
    "/{order_id}/confirm",
    response_model=ResponseModel[Order],
    summary="确认订单",
    description="商家确认订单"
)
async def confirm_order(
    order_id: str = Path(..., description="订单ID"),
    current_user_id = Depends(get_current_user_id),
    order_service = Depends(get_order_service)
):
    """确认订单
    
    - 商家确认订单，订单状态从待确认变为已确认
    - 只有商家可以确认订单
    """
    result = await order_service.update_order_status(
        order_id=order_id,
        new_status=OrderStatus.CONFIRMED,
        user_id=current_user_id,
        notes="商家确认订单"
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.put(
    "/{order_id}/ship",
    response_model=ResponseModel[Order],
    summary="发货",
    description="商家发货"
)
async def ship_order(
    order_id: str = Path(..., description="订单ID"),
    tracking_number: Optional[str] = Query(None, description="快递单号"),
    current_user_id = Depends(get_current_user_id),
    order_service = Depends(get_order_service)
):
    """发货
    
    - 商家发货，订单状态从已确认变为已发货
    - 可以提供快递单号
    - 只有商家可以发货
    """
    notes = f"商家发货"
    if tracking_number:
        notes += f"，快递单号：{tracking_number}"
    
    result = await order_service.update_order_status(
        order_id=order_id,
        new_status=OrderStatus.SHIPPED,
        user_id=current_user_id,
        notes=notes
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.put(
    "/{order_id}/deliver",
    response_model=ResponseModel[Order],
    summary="确认收货",
    description="买家确认收货"
)
async def deliver_order(
    order_id: str = Path(..., description="订单ID"),
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """确认收货
    
    - 买家确认收货，订单状态从已发货变为已完成
    - 买家和商家都可以操作（自动确认机制）
    """
    result = await order_service.update_order_status(
        order_id=order_id,
        new_status=OrderStatus.DELIVERED,
        user_id=current_user.id,
        notes="确认收货"
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.put(
    "/{order_id}/cancel",
    response_model=ResponseModel[Order],
    summary="取消订单",
    description="取消订单"
)
async def cancel_order(
    order_id: str = Path(..., description="订单ID"),
    reason: Optional[str] = Query(None, description="取消原因"),
    current_user: User = Depends(require_active_user),
    order_service = Depends(get_order_service)
):
    """取消订单
    
    - 买家和商家都可以取消订单
    - 取消后会自动恢复商品库存
    - 只能取消待确认或已确认状态的订单
    """
    notes = "取消订单"
    if reason:
        notes += f"，原因：{reason}"
    
    result = await order_service.update_order_status(
        order_id=order_id,
        new_status=OrderStatus.CANCELLED,
        user_id=current_user.id,
        notes=notes
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result