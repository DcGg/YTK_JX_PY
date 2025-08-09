"""达人关系管理API

实现达人关系的创建、查询、状态更新等功能。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..core.security import (
    get_current_user, require_role, require_active_user,
    rate_limit
)
from ..models.user import User, UserRole
from ..models.relationship import (
    RelationshipCreate, RelationshipUpdate, RelationshipType,
    RelationshipStatus, RelationshipListResponse, RelationshipStatistics,
    UserBindingInfo, RelationshipRequest, RelationshipApproval
)
from ..models.common import ResponseModel, PaginationParams
from ..services.relationship_service import (
    RelationshipService, get_relationship_service
)

# 创建路由器
router = APIRouter(prefix="/relationships", tags=["达人关系管理"])


@router.post("/", response_model=ResponseModel)
@rate_limit("relationship_create", 10, 60)  # 每分钟最多10次
async def create_relationship(
    relationship_data: RelationshipCreate,
    current_user: User = Depends(require_active_user),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """创建用户关系
    
    创建绑定、推荐、合作或关注关系。
    
    - **type**: 关系类型（binding/referral/partnership/follow）
    - **related_user_id**: 目标用户ID
    - **commission_rate**: 佣金比例（可选）
    - **notes**: 备注信息（可选）
    
    权限要求：
    - 所有活跃用户都可以创建关系
    - 系统会验证关系类型的合理性
    """
    try:
        result = await relationship_service.create_relationship(
            relationship_data=relationship_data,
            requester_id=current_user.id
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建关系API异常: {e}")
        raise HTTPException(status_code=500, detail="创建关系失败")


@router.put("/{relationship_id}/status", response_model=ResponseModel)
@rate_limit("relationship_update", 20, 60)  # 每分钟最多20次
async def update_relationship_status(
    relationship_id: str,
    new_status: RelationshipStatus,
    notes: Optional[str] = None,
    current_user: User = Depends(require_active_user),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """更新关系状态
    
    更新指定关系的状态。
    
    - **new_status**: 新状态（active/inactive/pending/rejected/expired/cancelled）
    - **notes**: 备注信息（可选）
    
    权限要求：
    - 关系的双方用户可以更新状态
    - 管理员可以更新任何关系状态
    """
    try:
        result = await relationship_service.update_relationship_status(
            relationship_id=relationship_id,
            new_status=new_status,
            operator_id=current_user.id,
            notes=notes
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新关系状态API异常: {e}")
        raise HTTPException(status_code=500, detail="更新关系状态失败")


@router.get("/my", response_model=ResponseModel[RelationshipListResponse])
@rate_limit("relationship_list", 30, 60)  # 每分钟最多30次
async def get_my_relationships(
    relationship_type: Optional[RelationshipType] = Query(None, description="关系类型过滤"),
    status: Optional[RelationshipStatus] = Query(None, description="状态过滤"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_active_user),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """获取我的关系列表
    
    获取当前用户的所有关系。
    
    查询参数：
    - **relationship_type**: 关系类型过滤（可选）
    - **status**: 状态过滤（可选）
    - **page**: 页码（默认1）
    - **page_size**: 每页数量（默认20）
    
    权限要求：
    - 只能查看自己的关系
    """
    try:
        result = await relationship_service.get_user_relationships(
            user_id=current_user.id,
            relationship_type=relationship_type,
            status=status,
            pagination=pagination
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取关系列表API异常: {e}")
        raise HTTPException(status_code=500, detail="获取关系列表失败")


@router.get("/binding-info", response_model=ResponseModel[UserBindingInfo])
@rate_limit("binding_info", 20, 60)  # 每分钟最多20次
async def get_my_binding_info(
    current_user: User = Depends(require_active_user),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """获取我的绑定信息
    
    获取当前用户的绑定关系详情，包括上级、下级和团队统计。
    
    返回信息：
    - **user_info**: 用户基本信息
    - **superior_info**: 上级信息（我绑定的人）
    - **subordinates_info**: 下级信息列表（绑定我的人）
    - **subordinates_count**: 下级数量
    - **team_performance**: 团队业绩统计
    
    权限要求：
    - 只能查看自己的绑定信息
    """
    try:
        result = await relationship_service.get_user_binding_info(
            user_id=current_user.id
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取绑定信息API异常: {e}")
        raise HTTPException(status_code=500, detail="获取绑定信息失败")


@router.get("/statistics", response_model=ResponseModel[RelationshipStatistics])
@rate_limit("relationship_stats", 10, 60)  # 每分钟最多10次
async def get_relationship_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(require_active_user),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """获取关系统计信息
    
    获取当前用户的关系统计数据。
    
    查询参数：
    - **days**: 统计天数（1-365天，默认30天）
    
    返回统计：
    - **total_bindings**: 总绑定数
    - **total_referrals**: 总推荐数
    - **total_partnerships**: 总合作数
    - **total_follows**: 总关注数
    - **recent_relationships**: 最近新增关系数
    
    权限要求：
    - 只能查看自己的统计信息
    """
    try:
        result = await relationship_service.get_relationship_statistics(
            user_id=current_user.id,
            days=days
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取关系统计API异常: {e}")
        raise HTTPException(status_code=500, detail="获取关系统计失败")


@router.get("/user/{user_id}", response_model=ResponseModel[RelationshipListResponse])
@rate_limit("user_relationships", 20, 60)  # 每分钟最多20次
async def get_user_relationships(
    user_id: str,
    relationship_type: Optional[RelationshipType] = Query(None, description="关系类型过滤"),
    status: Optional[RelationshipStatus] = Query(None, description="状态过滤"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.LEADER])),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """获取指定用户的关系列表
    
    管理员和团长可以查看其他用户的关系。
    
    路径参数：
    - **user_id**: 目标用户ID
    
    查询参数：
    - **relationship_type**: 关系类型过滤（可选）
    - **status**: 状态过滤（可选）
    - **page**: 页码（默认1）
    - **page_size**: 每页数量（默认20）
    
    权限要求：
    - 管理员：可以查看任何用户的关系
    - 团长：可以查看团队成员的关系
    """
    try:
        # 团长权限检查：只能查看自己团队成员的关系
        if current_user.role == UserRole.LEADER:
            # 检查目标用户是否为团队成员
            binding_result = await relationship_service.get_user_relationships(
                user_id=current_user.id,
                relationship_type=RelationshipType.BINDING,
                status=RelationshipStatus.ACTIVE
            )
            
            if binding_result.success:
                team_member_ids = [rel.related_user_id for rel in binding_result.data.items]
                if user_id not in team_member_ids:
                    raise HTTPException(status_code=403, detail="无权限查看此用户的关系")
            else:
                raise HTTPException(status_code=403, detail="无权限查看此用户的关系")
        
        result = await relationship_service.get_user_relationships(
            user_id=user_id,
            relationship_type=relationship_type,
            status=status,
            pagination=pagination
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户关系API异常: {e}")
        raise HTTPException(status_code=500, detail="获取用户关系失败")


@router.get("/user/{user_id}/binding-info", response_model=ResponseModel[UserBindingInfo])
@rate_limit("user_binding_info", 20, 60)  # 每分钟最多20次
async def get_user_binding_info(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.LEADER])),
    relationship_service: RelationshipService = Depends(get_relationship_service)
):
    """获取指定用户的绑定信息
    
    管理员和团长可以查看其他用户的绑定信息。
    
    路径参数：
    - **user_id**: 目标用户ID
    
    权限要求：
    - 管理员：可以查看任何用户的绑定信息
    - 团长：可以查看团队成员的绑定信息
    """
    try:
        # 团长权限检查：只能查看自己团队成员的绑定信息
        if current_user.role == UserRole.LEADER:
            # 检查目标用户是否为团队成员
            binding_result = await relationship_service.get_user_relationships(
                user_id=current_user.id,
                relationship_type=RelationshipType.BINDING,
                status=RelationshipStatus.ACTIVE
            )
            
            if binding_result.success:
                team_member_ids = [rel.related_user_id for rel in binding_result.data.items]
                if user_id not in team_member_ids:
                    raise HTTPException(status_code=403, detail="无权限查看此用户的绑定信息")
            else:
                raise HTTPException(status_code=403, detail="无权限查看此用户的绑定信息")
        
        result = await relationship_service.get_user_binding_info(
            user_id=user_id
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户绑定信息API异常: {e}")
        raise HTTPException(status_code=500, detail="获取用户绑定信息失败")


@router.get("/types", response_model=ResponseModel[list])
async def get_relationship_types():
    """获取关系类型列表
    
    返回所有可用的关系类型。
    
    权限要求：
    - 无需认证
    """
    try:
        types = [
            {
                "value": relationship_type.value,
                "label": {
                    "binding": "绑定关系",
                    "referral": "推荐关系",
                    "partnership": "合作关系",
                    "follow": "关注关系"
                }[relationship_type.value]
            }
            for relationship_type in RelationshipType
        ]
        
        return ResponseModel(
            success=True,
            message="获取关系类型成功",
            data=types
        )
        
    except Exception as e:
        logger.error(f"获取关系类型API异常: {e}")
        raise HTTPException(status_code=500, detail="获取关系类型失败")


@router.get("/statuses", response_model=ResponseModel[list])
async def get_relationship_statuses():
    """获取关系状态列表
    
    返回所有可用的关系状态。
    
    权限要求：
    - 无需认证
    """
    try:
        statuses = [
            {
                "value": status.value,
                "label": {
                    "active": "活跃",
                    "inactive": "非活跃",
                    "pending": "待处理",
                    "rejected": "已拒绝",
                    "expired": "已过期",
                    "cancelled": "已取消"
                }[status.value]
            }
            for status in RelationshipStatus
        ]
        
        return ResponseModel(
            success=True,
            message="获取关系状态成功",
            data=statuses
        )
        
    except Exception as e:
        logger.error(f"获取关系状态API异常: {e}")
        raise HTTPException(status_code=500, detail="获取关系状态失败")