"""申样管理API路由

实现申样请求、状态跟踪、审核处理等接口。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..models.sample import (
    Sample, SampleCreate, SampleUpdate, SampleResponse,
    SampleListResponse, SampleSearch, SampleStatistics,
    SampleStatus, SampleType, SampleBatchOperation,
    SampleApproval, SampleShipping, SampleReview
)
from ..models.user import User, UserRole
from ..models.common import (
    ResponseModel, PaginationParams, PaginationResponse
)
from ..core.security import (
    get_current_user_id, require_roles, require_active_user,
    create_rate_limit_dependency
)
from ..services.sample_service import SampleService, get_sample_service

# 创建路由器
router = APIRouter(prefix="/samples", tags=["申样管理"])


@router.post(
    "/",
    response_model=ResponseModel[Sample],
    summary="创建申样请求",
    description="达人和团长可以创建申样请求"
)
async def create_sample_request(
    sample_data: SampleCreate,
    current_user_id = Depends(get_current_user_id),
    sample_service: SampleService = Depends(get_sample_service),
    _: None = Depends(create_rate_limit_dependency(10, 60))  # 每分钟最多10次
):
    """创建申样请求"""
    try:
        result = await sample_service.create_sample_request(
            sample_data=sample_data,
            requester_id=current_user.id
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建申样请求异常: {e}")
        raise HTTPException(status_code=500, detail="创建申样请求失败")


@router.get(
    "/{sample_id}",
    response_model=ResponseModel[SampleResponse],
    summary="获取申样详情",
    description="获取指定申样的详细信息"
)
async def get_sample_detail(
    sample_id: str,
    current_user: User = Depends(require_active_user),
    sample_service: SampleService = Depends(get_sample_service)
):
    """获取申样详情"""
    try:
        result = await sample_service.get_sample_by_id(
            sample_id=sample_id,
            user_id=current_user.id
        )
        
        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取申样详情异常: {e}")
        raise HTTPException(status_code=500, detail="获取申样详情失败")


@router.put(
    "/{sample_id}/status",
    response_model=ResponseModel[Sample],
    summary="更新申样状态",
    description="更新申样的状态（审批、发货、收货等）"
)
async def update_sample_status(
    sample_id: str,
    new_status: SampleStatus,
    notes: Optional[str] = None,
    current_user: User = Depends(require_active_user),
    sample_service: SampleService = Depends(get_sample_service)
):
    """更新申样状态"""
    try:
        result = await sample_service.update_sample_status(
            sample_id=sample_id,
            new_status=new_status,
            operator_id=current_user_id,
            notes=notes
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新申样状态异常: {e}")
        raise HTTPException(status_code=500, detail="更新申样状态失败")


@router.get(
    "/",
    response_model=ResponseModel[SampleListResponse],
    summary="搜索申样记录",
    description="根据条件搜索申样记录"
)
async def search_samples(
    sample_number: Optional[str] = Query(None, description="申样编号"),
    product_id: Optional[str] = Query(None, description="商品ID"),
    requester_id: Optional[str] = Query(None, description="申请者ID"),
    merchant_id: Optional[str] = Query(None, description="商家ID"),
    type: Optional[SampleType] = Query(None, description="申样类型"),
    status: Optional[SampleStatus] = Query(None, description="申样状态"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(require_active_user),
    sample_service: SampleService = Depends(get_sample_service)
):
    """搜索申样记录"""
    try:
        search_params = SampleSearch(
            sample_number=sample_number,
            product_id=product_id,
            requester_id=requester_id,
            merchant_id=merchant_id,
            type=type,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        
        pagination = PaginationParams(page=page, page_size=page_size)
        
        result = await sample_service.search_samples(
            search_params=search_params,
            user_id=current_user_id,
            pagination=pagination
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索申样记录异常: {e}")
        raise HTTPException(status_code=500, detail="搜索申样记录失败")


@router.get(
    "/my/requests",
    response_model=ResponseModel[SampleListResponse],
    summary="获取我的申样请求",
    description="获取当前用户的申样请求列表"
)
async def get_my_sample_requests(
    status: Optional[SampleStatus] = Query(None, description="申样状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user_id = Depends(get_current_user_id),
    sample_service: SampleService = Depends(get_sample_service)
):
    """获取我的申样请求"""
    try:
        search_params = SampleSearch(
            requester_id=current_user.id,
            status=status
        )
        
        pagination = PaginationParams(page=page, page_size=page_size)
        
        result = await sample_service.search_samples(
            search_params=search_params,
            user_id=current_user_id,
            pagination=pagination
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取我的申样请求异常: {e}")
        raise HTTPException(status_code=500, detail="获取我的申样请求失败")


@router.get(
    "/merchant/pending",
    response_model=ResponseModel[SampleListResponse],
    summary="获取待处理的申样请求",
    description="商家获取待处理的申样请求列表"
)
async def get_pending_sample_requests(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user_id = Depends(get_current_user_id),
    sample_service: SampleService = Depends(get_sample_service)
):
    """获取待处理的申样请求"""
    try:
        search_params = SampleSearch(
            merchant_id=current_user_id,
            status=SampleStatus.PENDING
        )
        
        pagination = PaginationParams(page=page, page_size=page_size)
        
        result = await sample_service.search_samples(
            search_params=search_params,
            user_id=current_user.id,
            pagination=pagination
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取待处理申样请求异常: {e}")
        raise HTTPException(status_code=500, detail="获取待处理申样请求失败")


@router.post(
    "/{sample_id}/approve",
    response_model=ResponseModel[Sample],
    summary="审批申样请求",
    description="商家审批申样请求"
)
async def approve_sample_request(
    sample_id: str,
    approval_data: SampleApproval,
    current_user_id = Depends(get_current_user_id),
    sample_service: SampleService = Depends(get_sample_service)
):
    """审批申样请求"""
    try:
        result = await sample_service.update_sample_status(
            sample_id=sample_id,
            new_status=SampleStatus.APPROVED if approval_data.approved else SampleStatus.REJECTED,
            operator_id=current_user_id,
            notes=approval_data.notes
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审批申样请求异常: {e}")
        raise HTTPException(status_code=500, detail="审批申样请求失败")


@router.post(
    "/{sample_id}/ship",
    response_model=ResponseModel[Sample],
    summary="发货申样",
    description="商家发货申样"
)
async def ship_sample(
    sample_id: str,
    shipping_data: SampleShipping,
    current_user_id = Depends(get_current_user_id),
    sample_service: SampleService = Depends(get_sample_service)
):
    """发货申样"""
    try:
        # 这里可以添加物流信息更新逻辑
        result = await sample_service.update_sample_status(
            sample_id=sample_id,
            new_status=SampleStatus.SHIPPED,
            operator_id=current_user_id,
            notes=f"快递公司: {shipping_data.express_company}, 快递单号: {shipping_data.tracking_number}"
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发货申样异常: {e}")
        raise HTTPException(status_code=500, detail="发货申样失败")


@router.post(
    "/{sample_id}/confirm-delivery",
    response_model=ResponseModel[Sample],
    summary="确认收货",
    description="申请者确认收到样品"
)
async def confirm_sample_delivery(
    sample_id: str,
    current_user_id = Depends(get_current_user_id),
    sample_service: SampleService = Depends(get_sample_service)
):
    """确认收货"""
    try:
        result = await sample_service.update_sample_status(
            sample_id=sample_id,
            new_status=SampleStatus.DELIVERED,
            operator_id=current_user_id,
            notes="用户确认收货"
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认收货异常: {e}")
        raise HTTPException(status_code=500, detail="确认收货失败")


@router.post(
    "/{sample_id}/return",
    response_model=ResponseModel[Sample],
    summary="退回样品",
    description="申请者退回样品"
)
async def return_sample(
    sample_id: str,
    review_data: SampleReview,
    current_user: User = Depends(require_roles([UserRole.INFLUENCER, UserRole.LEADER])),
    sample_service: SampleService = Depends(get_sample_service)
):
    """退回样品"""
    try:
        result = await sample_service.update_sample_status(
            sample_id=sample_id,
            new_status=SampleStatus.RETURNED,
            operator_id=current_user_id,
            notes=f"评价: {review_data.rating}/5, 反馈: {review_data.feedback}"
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"退回样品异常: {e}")
        raise HTTPException(status_code=500, detail="退回样品失败")


@router.get(
    "/statistics/overview",
    response_model=ResponseModel[SampleStatistics],
    summary="获取申样统计",
    description="获取申样统计信息"
)
async def get_sample_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(require_active_user),
    sample_service: SampleService = Depends(get_sample_service)
):
    """获取申样统计"""
    try:
        result = await sample_service.get_sample_statistics(
            user_id=current_user.id,
            days=days
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取申样统计异常: {e}")
        raise HTTPException(status_code=500, detail="获取申样统计失败")


@router.get(
    "/types",
    response_model=ResponseModel[List[dict]],
    summary="获取申样类型列表",
    description="获取所有可用的申样类型"
)
async def get_sample_types():
    """获取申样类型列表"""
    try:
        types = [
            {"value": sample_type.value, "label": sample_type.value}
            for sample_type in SampleType
        ]
        
        return ResponseModel(
            success=True,
            message="获取申样类型成功",
            data=types
        )
        
    except Exception as e:
        logger.error(f"获取申样类型异常: {e}")
        raise HTTPException(status_code=500, detail="获取申样类型失败")


@router.get(
    "/statuses",
    response_model=ResponseModel[List[dict]],
    summary="获取申样状态列表",
    description="获取所有可用的申样状态"
)
async def get_sample_statuses():
    """获取申样状态列表"""
    try:
        statuses = [
            {"value": status.value, "label": status.value}
            for status in SampleStatus
        ]
        
        return ResponseModel(
            success=True,
            message="获取申样状态成功",
            data=statuses
        )
        
    except Exception as e:
        logger.error(f"获取申样状态异常: {e}")
        raise HTTPException(status_code=500, detail="获取申样状态失败")