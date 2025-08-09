"""达人关系服务

实现达人信息管理、绑定关系、数据分析等功能。

Author: 云推客严选开发团队
Date: 2024
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from loguru import logger
from supabase import Client

from ..core.database import get_db_client
from ..models.relationship import (
    UserRelationship, RelationshipCreate, RelationshipUpdate,
    RelationshipResponse, RelationshipListResponse, RelationshipSearch,
    RelationshipStatistics, RelationshipType, RelationshipStatus,
    RelationshipRequest, RelationshipApproval, RelationshipBatchOperation,
    UserBindingInfo, TeamPerformance, CommissionRule
)
from ..models.user import User, UserRole
from ..models.common import (
    ResponseModel, PaginationParams, PaginationResponse
)


class RelationshipService:
    """达人关系服务类
    
    提供达人关系相关的所有业务功能。
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    async def create_relationship(
        self, 
        relationship_data: RelationshipCreate,
        requester_id: str
    ) -> ResponseModel[UserRelationship]:
        """创建用户关系
        
        Args:
            relationship_data: 关系创建数据
            requester_id: 请求者ID
            
        Returns:
            ResponseModel[UserRelationship]: 创建结果
        """
        try:
            # 验证用户是否存在
            user_result = self.supabase.table("users").select(
                "id, role"
            ).eq("id", relationship_data.related_user_id).execute()
            
            if not user_result.data:
                return ResponseModel(
                    success=False,
                    message="目标用户不存在",
                    data=None
                )
            
            target_user = user_result.data[0]
            
            # 检查是否已存在关系
            existing_result = self.supabase.table("user_relationships").select(
                "id"
            ).eq("user_id", requester_id).eq(
                "related_user_id", relationship_data.related_user_id
            ).eq("type", relationship_data.type.value).execute()
            
            if existing_result.data:
                return ResponseModel(
                    success=False,
                    message="关系已存在",
                    data=None
                )
            
            # 验证关系类型的合理性
            requester_result = self.supabase.table("users").select(
                "id, role"
            ).eq("id", requester_id).execute()
            
            if not requester_result.data:
                return ResponseModel(
                    success=False,
                    message="请求者不存在",
                    data=None
                )
            
            requester_role = requester_result.data[0]["role"]
            target_role = target_user["role"]
            
            # 验证关系类型规则
            if not self._validate_relationship_type(
                relationship_data.type, requester_role, target_role
            ):
                return ResponseModel(
                    success=False,
                    message="不支持的关系类型",
                    data=None
                )
            
            # 生成关系ID
            relationship_id = str(uuid.uuid4())
            
            # 确定初始状态
            initial_status = RelationshipStatus.PENDING
            if relationship_data.type == RelationshipType.FOLLOW:
                initial_status = RelationshipStatus.ACTIVE  # 关注直接生效
            
            # 构造关系数据
            db_relationship_data = {
                "id": relationship_id,
                "user_id": requester_id,
                "related_user_id": relationship_data.related_user_id,
                "type": relationship_data.type.value,
                "status": initial_status.value,
                "commission_rate": float(relationship_data.commission_rate or 0),
                "notes": relationship_data.notes,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 插入关系
            result = self.supabase.table("user_relationships").insert(
                db_relationship_data
            ).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="关系创建失败",
                    data=None
                )
            
            relationship = UserRelationship(**result.data[0])
            
            logger.info(f"用户关系创建成功: {requester_id} -> {relationship_data.related_user_id}")
            return ResponseModel(
                success=True,
                message="关系创建成功",
                data=relationship
            )
            
        except Exception as e:
            logger.error(f"创建用户关系异常: {e}")
            return ResponseModel(
                success=False,
                message=f"关系创建失败: {str(e)}",
                data=None
            )
    
    async def update_relationship_status(
        self, 
        relationship_id: str,
        new_status: RelationshipStatus,
        operator_id: str,
        notes: Optional[str] = None
    ) -> ResponseModel[UserRelationship]:
        """更新关系状态
        
        Args:
            relationship_id: 关系ID
            new_status: 新状态
            operator_id: 操作者ID
            notes: 备注
            
        Returns:
            ResponseModel[UserRelationship]: 更新结果
        """
        try:
            # 获取关系信息
            relationship_result = self.supabase.table("user_relationships").select(
                "*"
            ).eq("id", relationship_id).execute()
            
            if not relationship_result.data:
                return ResponseModel(
                    success=False,
                    message="关系不存在",
                    data=None
                )
            
            relationship_data = relationship_result.data[0]
            
            # 权限检查：只有关系的双方或管理员可以更新状态
            if operator_id not in [relationship_data["user_id"], relationship_data["related_user_id"]]:
                # 检查是否为管理员
                operator_result = self.supabase.table("users").select(
                    "role"
                ).eq("id", operator_id).execute()
                
                if not operator_result.data or operator_result.data[0]["role"] != UserRole.ADMIN.value:
                    return ResponseModel(
                        success=False,
                        message="无权限操作此关系",
                        data=None
                    )
            
            # 验证状态转换的合理性
            current_status = RelationshipStatus(relationship_data["status"])
            if not self._validate_status_transition(current_status, new_status):
                return ResponseModel(
                    success=False,
                    message="无效的状态转换",
                    data=None
                )
            
            # 构造更新数据
            update_data = {
                "status": new_status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if notes:
                update_data["notes"] = notes
            
            # 如果是激活关系，设置生效时间
            if new_status == RelationshipStatus.ACTIVE and current_status != RelationshipStatus.ACTIVE:
                update_data["effective_date"] = datetime.utcnow().isoformat()
            
            # 更新关系
            result = self.supabase.table("user_relationships").update(
                update_data
            ).eq("id", relationship_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="关系状态更新失败",
                    data=None
                )
            
            relationship = UserRelationship(**result.data[0])
            
            logger.info(f"关系状态更新成功: {relationship_id} -> {new_status.value}")
            return ResponseModel(
                success=True,
                message="关系状态更新成功",
                data=relationship
            )
            
        except Exception as e:
            logger.error(f"更新关系状态异常: {e}")
            return ResponseModel(
                success=False,
                message=f"关系状态更新失败: {str(e)}",
                data=None
            )
    
    async def get_user_relationships(
        self, 
        user_id: str,
        relationship_type: Optional[RelationshipType] = None,
        status: Optional[RelationshipStatus] = None,
        pagination: PaginationParams = PaginationParams()
    ) -> ResponseModel[RelationshipListResponse]:
        """获取用户关系列表
        
        Args:
            user_id: 用户ID
            relationship_type: 关系类型过滤
            status: 状态过滤
            pagination: 分页参数
            
        Returns:
            ResponseModel[RelationshipListResponse]: 关系列表
        """
        try:
            # 构建查询
            query = self.supabase.table("user_relationships").select(
                "*, related_user:users!user_relationships_related_user_id_fkey(id, nickname, avatar_url, role)",
                count="exact"
            ).eq("user_id", user_id)
            
            # 类型过滤
            if relationship_type:
                query = query.eq("type", relationship_type.value)
            
            # 状态过滤
            if status:
                query = query.eq("status", status.value)
            
            # 排序
            query = query.order("created_at", desc=True)
            
            # 分页
            offset = (pagination.page - 1) * pagination.page_size
            query = query.range(offset, offset + pagination.page_size - 1)
            
            # 执行查询
            result = query.execute()
            
            # 构造响应数据
            relationships = []
            for item in result.data:
                related_user_info = item.pop("related_user", None)
                relationship_response = RelationshipResponse(
                    **item,
                    related_user_info=related_user_info
                )
                relationships.append(relationship_response)
            
            # 分页信息
            total = result.count or 0
            pagination_response = PaginationResponse(
                page=pagination.page,
                page_size=pagination.page_size,
                total=total,
                pages=(total + pagination.page_size - 1) // pagination.page_size
            )
            
            list_response = RelationshipListResponse(
                items=relationships,
                pagination=pagination_response
            )
            
            return ResponseModel(
                success=True,
                message="获取用户关系成功",
                data=list_response
            )
            
        except Exception as e:
            logger.error(f"获取用户关系异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取用户关系失败: {str(e)}",
                data=None
            )
    
    async def get_user_binding_info(
        self, 
        user_id: str
    ) -> ResponseModel[UserBindingInfo]:
        """获取用户绑定信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            ResponseModel[UserBindingInfo]: 绑定信息
        """
        try:
            # 获取用户基本信息
            user_result = self.supabase.table("users").select(
                "id, nickname, avatar_url, role, phone, wechat_openid"
            ).eq("id", user_id).execute()
            
            if not user_result.data:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=None
                )
            
            user_info = user_result.data[0]
            
            # 获取上级关系（我绑定的人）
            superior_result = self.supabase.table("user_relationships").select(
                "*, related_user:users!user_relationships_related_user_id_fkey(id, nickname, avatar_url, role)"
            ).eq("user_id", user_id).eq(
                "type", RelationshipType.BINDING.value
            ).eq("status", RelationshipStatus.ACTIVE.value).execute()
            
            superior_info = None
            if superior_result.data:
                superior_data = superior_result.data[0]
                superior_info = superior_data["related_user"]
            
            # 获取下级关系（绑定我的人）
            subordinates_result = self.supabase.table("user_relationships").select(
                "*, user:users!user_relationships_user_id_fkey(id, nickname, avatar_url, role)"
            ).eq("related_user_id", user_id).eq(
                "type", RelationshipType.BINDING.value
            ).eq("status", RelationshipStatus.ACTIVE.value).execute()
            
            subordinates_info = []
            for item in subordinates_result.data:
                subordinates_info.append(item["user"])
            
            # 获取团队统计
            team_stats = await self._get_team_statistics(user_id)
            
            binding_info = UserBindingInfo(
                user_info=user_info,
                superior_info=superior_info,
                subordinates_info=subordinates_info,
                subordinates_count=len(subordinates_info),
                team_performance=team_stats
            )
            
            return ResponseModel(
                success=True,
                message="获取绑定信息成功",
                data=binding_info
            )
            
        except Exception as e:
            logger.error(f"获取用户绑定信息异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取绑定信息失败: {str(e)}",
                data=None
            )
    
    async def get_relationship_statistics(
        self, 
        user_id: str,
        days: int = 30
    ) -> ResponseModel[RelationshipStatistics]:
        """获取关系统计信息
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            ResponseModel[RelationshipStatistics]: 统计信息
        """
        try:
            # 计算时间范围
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 获取各类型关系统计
            binding_count_result = self.supabase.table("user_relationships").select(
                "*", count="exact"
            ).eq("related_user_id", user_id).eq(
                "type", RelationshipType.BINDING.value
            ).eq("status", RelationshipStatus.ACTIVE.value).execute()
            
            referral_count_result = self.supabase.table("user_relationships").select(
                "*", count="exact"
            ).eq("user_id", user_id).eq(
                "type", RelationshipType.REFERRAL.value
            ).eq("status", RelationshipStatus.ACTIVE.value).execute()
            
            partnership_count_result = self.supabase.table("user_relationships").select(
                "*", count="exact"
            ).eq("user_id", user_id).eq(
                "type", RelationshipType.PARTNERSHIP.value
            ).eq("status", RelationshipStatus.ACTIVE.value).execute()
            
            follow_count_result = self.supabase.table("user_relationships").select(
                "*", count="exact"
            ).eq("user_id", user_id).eq(
                "type", RelationshipType.FOLLOW.value
            ).eq("status", RelationshipStatus.ACTIVE.value).execute()
            
            # 获取最近新增关系
            recent_relationships_result = self.supabase.table("user_relationships").select(
                "*", count="exact"
            ).eq("user_id", user_id).gte(
                "created_at", start_date.isoformat()
            ).execute()
            
            statistics = RelationshipStatistics(
                total_bindings=binding_count_result.count or 0,
                total_referrals=referral_count_result.count or 0,
                total_partnerships=partnership_count_result.count or 0,
                total_follows=follow_count_result.count or 0,
                recent_relationships=recent_relationships_result.count or 0
            )
            
            return ResponseModel(
                success=True,
                message="获取关系统计成功",
                data=statistics
            )
            
        except Exception as e:
            logger.error(f"获取关系统计异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取关系统计失败: {str(e)}",
                data=None
            )
    
    def _validate_relationship_type(
        self, 
        relationship_type: RelationshipType,
        requester_role: str,
        target_role: str
    ) -> bool:
        """验证关系类型的合理性
        
        Args:
            relationship_type: 关系类型
            requester_role: 请求者角色
            target_role: 目标用户角色
            
        Returns:
            bool: 是否合理
        """
        # 绑定关系：达人/团长可以绑定商家，用户可以绑定达人/团长
        if relationship_type == RelationshipType.BINDING:
            if requester_role in [UserRole.INFLUENCER.value, UserRole.LEADER.value]:
                return target_role == UserRole.MERCHANT.value
            elif requester_role == UserRole.USER.value:
                return target_role in [UserRole.INFLUENCER.value, UserRole.LEADER.value]
        
        # 推荐关系：任何人都可以推荐
        elif relationship_type == RelationshipType.REFERRAL:
            return True
        
        # 合作关系：商家和达人/团长之间
        elif relationship_type == RelationshipType.PARTNERSHIP:
            return (
                (requester_role == UserRole.MERCHANT.value and target_role in [UserRole.INFLUENCER.value, UserRole.LEADER.value]) or
                (requester_role in [UserRole.INFLUENCER.value, UserRole.LEADER.value] and target_role == UserRole.MERCHANT.value)
            )
        
        # 关注关系：任何人都可以关注任何人
        elif relationship_type == RelationshipType.FOLLOW:
            return True
        
        return False
    
    def _validate_status_transition(
        self, 
        current_status: RelationshipStatus,
        new_status: RelationshipStatus
    ) -> bool:
        """验证状态转换的合理性
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            
        Returns:
            bool: 是否合理
        """
        # 定义允许的状态转换
        allowed_transitions = {
            RelationshipStatus.PENDING: [RelationshipStatus.ACTIVE, RelationshipStatus.REJECTED, RelationshipStatus.CANCELLED],
            RelationshipStatus.ACTIVE: [RelationshipStatus.INACTIVE, RelationshipStatus.EXPIRED, RelationshipStatus.CANCELLED],
            RelationshipStatus.INACTIVE: [RelationshipStatus.ACTIVE, RelationshipStatus.CANCELLED],
            RelationshipStatus.REJECTED: [RelationshipStatus.PENDING],
            RelationshipStatus.EXPIRED: [RelationshipStatus.ACTIVE],
            RelationshipStatus.CANCELLED: [RelationshipStatus.PENDING]
        }
        
        return new_status in allowed_transitions.get(current_status, [])
    
    async def _get_team_statistics(self, user_id: str) -> TeamPerformance:
        """获取团队统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            TeamPerformance: 团队表现数据
        """
        try:
            # 获取团队成员ID列表
            team_members_result = self.supabase.table("user_relationships").select(
                "user_id"
            ).eq("related_user_id", user_id).eq(
                "type", RelationshipType.BINDING.value
            ).eq("status", RelationshipStatus.ACTIVE.value).execute()
            
            team_member_ids = [item["user_id"] for item in team_members_result.data]
            team_member_ids.append(user_id)  # 包含自己
            
            # 这里可以根据实际业务需求计算团队业绩
            # 例如：团队订单数、销售额、佣金等
            # 由于没有具体的业绩表，这里返回默认值
            
            return TeamPerformance(
                total_orders=0,
                total_sales=Decimal("0.00"),
                total_commission=Decimal("0.00"),
                team_size=len(team_member_ids)
            )
            
        except Exception as e:
            logger.error(f"获取团队统计异常: {e}")
            return TeamPerformance(
                total_orders=0,
                total_sales=Decimal("0.00"),
                total_commission=Decimal("0.00"),
                team_size=0
            )


# 依赖注入函数
def get_relationship_service() -> RelationshipService:
    """获取关系服务实例"""
    supabase = get_db_client()
    return RelationshipService(supabase)