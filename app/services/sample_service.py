"""申样管理服务

实现申样请求、状态跟踪、审核处理等功能。

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
from ..services.product_service import ProductService, get_product_service


class SampleService:
    """申样管理服务类
    
    提供申样相关的所有业务功能。
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.product_service = get_product_service()
    
    async def create_sample_request(
        self, 
        sample_data: SampleCreate,
        requester_id: str
    ) -> ResponseModel[Sample]:
        """创建申样请求
        
        Args:
            sample_data: 申样创建数据
            requester_id: 申请者ID
            
        Returns:
            ResponseModel[Sample]: 创建结果
        """
        try:
            # 验证商品是否存在
            product_result = await self.product_service.get_product_by_id(
                product_id=sample_data.product_id
            )
            
            if not product_result.success or not product_result.data:
                return ResponseModel(
                    success=False,
                    message="商品不存在",
                    data=None
                )
            
            product = product_result.data
            
            # 检查商品是否支持申样
            if not product.allow_sample:
                return ResponseModel(
                    success=False,
                    message="该商品不支持申样",
                    data=None
                )
            
            # 验证申请者角色
            user_result = self.supabase.table("users").select(
                "id, role, nickname"
            ).eq("id", requester_id).execute()
            
            if not user_result.data:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=None
                )
            
            user_role = user_result.data[0]["role"]
            if user_role not in [UserRole.INFLUENCER.value, UserRole.LEADER.value]:
                return ResponseModel(
                    success=False,
                    message="只有达人和团长可以申请样品",
                    data=None
                )
            
            # 检查是否已有待处理的申样请求
            existing_result = self.supabase.table("samples").select(
                "id"
            ).eq("product_id", sample_data.product_id).eq(
                "requester_id", requester_id
            ).in_("status", [SampleStatus.PENDING.value, SampleStatus.APPROVED.value]).execute()
            
            if existing_result.data:
                return ResponseModel(
                    success=False,
                    message="该商品已有待处理的申样请求",
                    data=None
                )
            
            # 生成申样ID和编号
            sample_id = str(uuid.uuid4())
            sample_number = self._generate_sample_number()
            
            # 构造申样数据
            db_sample_data = {
                "id": sample_id,
                "sample_number": sample_number,
                "product_id": sample_data.product_id,
                "requester_id": requester_id,
                "merchant_id": product.merchant_id,
                "type": sample_data.type.value,
                "status": SampleStatus.PENDING.value,
                "quantity": sample_data.quantity,
                "reason": sample_data.reason,
                "expected_return_date": sample_data.expected_return_date.isoformat() if sample_data.expected_return_date else None,
                "shipping_address": sample_data.shipping_address,
                "contact_phone": sample_data.contact_phone,
                "contact_name": sample_data.contact_name,
                "notes": sample_data.notes,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 插入申样记录
            result = self.supabase.table("samples").insert(
                db_sample_data
            ).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="申样请求创建失败",
                    data=None
                )
            
            sample = Sample(**result.data[0])
            
            logger.info(f"申样请求创建成功: {sample_number} by {requester_id}")
            return ResponseModel(
                success=True,
                message="申样请求创建成功",
                data=sample
            )
            
        except Exception as e:
            logger.error(f"创建申样请求异常: {e}")
            return ResponseModel(
                success=False,
                message=f"申样请求创建失败: {str(e)}",
                data=None
            )
    
    async def update_sample_status(
        self, 
        sample_id: str,
        new_status: SampleStatus,
        operator_id: str,
        notes: Optional[str] = None
    ) -> ResponseModel[Sample]:
        """更新申样状态
        
        Args:
            sample_id: 申样ID
            new_status: 新状态
            operator_id: 操作者ID
            notes: 备注
            
        Returns:
            ResponseModel[Sample]: 更新结果
        """
        try:
            # 获取申样信息
            sample_result = self.supabase.table("samples").select(
                "*"
            ).eq("id", sample_id).execute()
            
            if not sample_result.data:
                return ResponseModel(
                    success=False,
                    message="申样记录不存在",
                    data=None
                )
            
            sample_data = sample_result.data[0]
            current_status = SampleStatus(sample_data["status"])
            
            # 权限检查
            operator_result = self.supabase.table("users").select(
                "role"
            ).eq("id", operator_id).execute()
            
            if not operator_result.data:
                return ResponseModel(
                    success=False,
                    message="操作者不存在",
                    data=None
                )
            
            operator_role = operator_result.data[0]["role"]
            
            # 权限验证
            if not self._validate_status_update_permission(
                current_status, new_status, operator_role, 
                operator_id, sample_data["merchant_id"], sample_data["requester_id"]
            ):
                return ResponseModel(
                    success=False,
                    message="无权限执行此操作",
                    data=None
                )
            
            # 验证状态转换的合理性
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
            
            # 根据状态设置特定字段
            if new_status == SampleStatus.APPROVED:
                update_data["approved_at"] = datetime.utcnow().isoformat()
                update_data["approved_by"] = operator_id
            elif new_status == SampleStatus.SHIPPED:
                update_data["shipped_at"] = datetime.utcnow().isoformat()
            elif new_status == SampleStatus.DELIVERED:
                update_data["delivered_at"] = datetime.utcnow().isoformat()
            elif new_status == SampleStatus.RETURNED:
                update_data["returned_at"] = datetime.utcnow().isoformat()
            elif new_status == SampleStatus.REJECTED:
                update_data["rejected_at"] = datetime.utcnow().isoformat()
                update_data["rejected_by"] = operator_id
            
            # 更新申样状态
            result = self.supabase.table("samples").update(
                update_data
            ).eq("id", sample_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="申样状态更新失败",
                    data=None
                )
            
            sample = Sample(**result.data[0])
            
            logger.info(f"申样状态更新成功: {sample_id} -> {new_status.value}")
            return ResponseModel(
                success=True,
                message="申样状态更新成功",
                data=sample
            )
            
        except Exception as e:
            logger.error(f"更新申样状态异常: {e}")
            return ResponseModel(
                success=False,
                message=f"申样状态更新失败: {str(e)}",
                data=None
            )
    
    async def get_sample_by_id(
        self, 
        sample_id: str,
        user_id: str
    ) -> ResponseModel[SampleResponse]:
        """根据ID获取申样详情
        
        Args:
            sample_id: 申样ID
            user_id: 用户ID
            
        Returns:
            ResponseModel[SampleResponse]: 申样详情
        """
        try:
            # 获取申样信息（包含关联数据）
            result = self.supabase.table("samples").select(
                "*, product:products(id, name, images, price, merchant_id), requester:users!samples_requester_id_fkey(id, nickname, avatar_url), merchant:users!samples_merchant_id_fkey(id, nickname, avatar_url)"
            ).eq("id", sample_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="申样记录不存在",
                    data=None
                )
            
            sample_data = result.data[0]
            
            # 权限检查：只有相关用户可以查看
            user_result = self.supabase.table("users").select(
                "role"
            ).eq("id", user_id).execute()
            
            if not user_result.data:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=None
                )
            
            user_role = user_result.data[0]["role"]
            
            # 权限验证
            if user_role != UserRole.ADMIN.value and user_id not in [
                sample_data["requester_id"], sample_data["merchant_id"]
            ]:
                return ResponseModel(
                    success=False,
                    message="无权限查看此申样记录",
                    data=None
                )
            
            # 构造响应数据
            product_info = sample_data.pop("product", None)
            requester_info = sample_data.pop("requester", None)
            merchant_info = sample_data.pop("merchant", None)
            
            sample_response = SampleResponse(
                **sample_data,
                product_info=product_info,
                requester_info=requester_info,
                merchant_info=merchant_info
            )
            
            return ResponseModel(
                success=True,
                message="获取申样详情成功",
                data=sample_response
            )
            
        except Exception as e:
            logger.error(f"获取申样详情异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取申样详情失败: {str(e)}",
                data=None
            )
    
    async def search_samples(
        self, 
        search_params: SampleSearch,
        user_id: str,
        pagination: PaginationParams = PaginationParams()
    ) -> ResponseModel[SampleListResponse]:
        """搜索申样记录
        
        Args:
            search_params: 搜索参数
            user_id: 用户ID
            pagination: 分页参数
            
        Returns:
            ResponseModel[SampleListResponse]: 申样列表
        """
        try:
            # 获取用户角色
            user_result = self.supabase.table("users").select(
                "role"
            ).eq("id", user_id).execute()
            
            if not user_result.data:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=None
                )
            
            user_role = user_result.data[0]["role"]
            
            # 构建查询
            query = self.supabase.table("samples").select(
                "*, product:products(id, name, images, price), requester:users!samples_requester_id_fkey(id, nickname, avatar_url), merchant:users!samples_merchant_id_fkey(id, nickname, avatar_url)",
                count="exact"
            )
            
            # 权限过滤：非管理员只能看到自己相关的申样
            if user_role != UserRole.ADMIN.value:
                if user_role == UserRole.MERCHANT.value:
                    query = query.eq("merchant_id", user_id)
                else:
                    query = query.eq("requester_id", user_id)
            
            # 搜索条件
            if search_params.sample_number:
                query = query.ilike("sample_number", f"%{search_params.sample_number}%")
            
            if search_params.product_id:
                query = query.eq("product_id", search_params.product_id)
            
            if search_params.requester_id:
                query = query.eq("requester_id", search_params.requester_id)
            
            if search_params.merchant_id:
                query = query.eq("merchant_id", search_params.merchant_id)
            
            if search_params.type:
                query = query.eq("type", search_params.type.value)
            
            if search_params.status:
                query = query.eq("status", search_params.status.value)
            
            if search_params.start_date:
                query = query.gte("created_at", search_params.start_date.isoformat())
            
            if search_params.end_date:
                query = query.lte("created_at", search_params.end_date.isoformat())
            
            # 排序
            query = query.order("created_at", desc=True)
            
            # 分页
            offset = (pagination.page - 1) * pagination.page_size
            query = query.range(offset, offset + pagination.page_size - 1)
            
            # 执行查询
            result = query.execute()
            
            # 构造响应数据
            samples = []
            for item in result.data:
                product_info = item.pop("product", None)
                requester_info = item.pop("requester", None)
                merchant_info = item.pop("merchant", None)
                
                sample_response = SampleResponse(
                    **item,
                    product_info=product_info,
                    requester_info=requester_info,
                    merchant_info=merchant_info
                )
                samples.append(sample_response)
            
            # 分页信息
            total = result.count or 0
            pagination_response = PaginationResponse(
                page=pagination.page,
                page_size=pagination.page_size,
                total=total,
                pages=(total + pagination.page_size - 1) // pagination.page_size
            )
            
            list_response = SampleListResponse(
                items=samples,
                pagination=pagination_response
            )
            
            return ResponseModel(
                success=True,
                message="搜索申样记录成功",
                data=list_response
            )
            
        except Exception as e:
            logger.error(f"搜索申样记录异常: {e}")
            return ResponseModel(
                success=False,
                message=f"搜索申样记录失败: {str(e)}",
                data=None
            )
    
    async def get_sample_statistics(
        self, 
        user_id: str,
        days: int = 30
    ) -> ResponseModel[SampleStatistics]:
        """获取申样统计信息
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            ResponseModel[SampleStatistics]: 统计信息
        """
        try:
            # 获取用户角色
            user_result = self.supabase.table("users").select(
                "role"
            ).eq("id", user_id).execute()
            
            if not user_result.data:
                return ResponseModel(
                    success=False,
                    message="用户不存在",
                    data=None
                )
            
            user_role = user_result.data[0]["role"]
            
            # 计算时间范围
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 构建基础查询
            base_query = self.supabase.table("samples").select("*", count="exact")
            
            # 权限过滤
            if user_role != UserRole.ADMIN.value:
                if user_role == UserRole.MERCHANT.value:
                    base_query = base_query.eq("merchant_id", user_id)
                else:
                    base_query = base_query.eq("requester_id", user_id)
            
            # 获取各状态统计
            total_result = base_query.execute()
            pending_result = base_query.eq("status", SampleStatus.PENDING.value).execute()
            approved_result = base_query.eq("status", SampleStatus.APPROVED.value).execute()
            shipped_result = base_query.eq("status", SampleStatus.SHIPPED.value).execute()
            delivered_result = base_query.eq("status", SampleStatus.DELIVERED.value).execute()
            returned_result = base_query.eq("status", SampleStatus.RETURNED.value).execute()
            rejected_result = base_query.eq("status", SampleStatus.REJECTED.value).execute()
            
            # 获取最近申样统计
            recent_result = base_query.gte(
                "created_at", start_date.isoformat()
            ).execute()
            
            statistics = SampleStatistics(
                total_samples=total_result.count or 0,
                pending_samples=pending_result.count or 0,
                approved_samples=approved_result.count or 0,
                shipped_samples=shipped_result.count or 0,
                delivered_samples=delivered_result.count or 0,
                returned_samples=returned_result.count or 0,
                rejected_samples=rejected_result.count or 0,
                recent_samples=recent_result.count or 0
            )
            
            return ResponseModel(
                success=True,
                message="获取申样统计成功",
                data=statistics
            )
            
        except Exception as e:
            logger.error(f"获取申样统计异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取申样统计失败: {str(e)}",
                data=None
            )
    
    def _generate_sample_number(self) -> str:
        """生成申样编号
        
        Returns:
            str: 申样编号
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = str(uuid.uuid4())[:8].upper()
        return f"SP{timestamp}{random_suffix}"
    
    def _validate_status_update_permission(
        self, 
        current_status: SampleStatus,
        new_status: SampleStatus,
        operator_role: str,
        operator_id: str,
        merchant_id: str,
        requester_id: str
    ) -> bool:
        """验证状态更新权限
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            operator_role: 操作者角色
            operator_id: 操作者ID
            merchant_id: 商家ID
            requester_id: 申请者ID
            
        Returns:
            bool: 是否有权限
        """
        # 管理员可以执行任何操作
        if operator_role == UserRole.ADMIN.value:
            return True
        
        # 商家权限
        if operator_id == merchant_id:
            # 商家可以审批、发货、拒绝
            if new_status in [SampleStatus.APPROVED, SampleStatus.SHIPPED, SampleStatus.REJECTED]:
                return True
        
        # 申请者权限
        if operator_id == requester_id:
            # 申请者可以确认收货、退回样品、取消申请
            if new_status in [SampleStatus.DELIVERED, SampleStatus.RETURNED, SampleStatus.CANCELLED]:
                return True
        
        return False
    
    def _validate_status_transition(
        self, 
        current_status: SampleStatus,
        new_status: SampleStatus
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
            SampleStatus.PENDING: [SampleStatus.APPROVED, SampleStatus.REJECTED, SampleStatus.CANCELLED],
            SampleStatus.APPROVED: [SampleStatus.SHIPPED, SampleStatus.CANCELLED],
            SampleStatus.SHIPPED: [SampleStatus.DELIVERED, SampleStatus.CANCELLED],
            SampleStatus.DELIVERED: [SampleStatus.RETURNED, SampleStatus.EXPIRED],
            SampleStatus.RETURNED: [],
            SampleStatus.REJECTED: [],
            SampleStatus.CANCELLED: [],
            SampleStatus.EXPIRED: [SampleStatus.RETURNED]
        }
        
        return new_status in allowed_transitions.get(current_status, [])


# 依赖注入函数
def get_sample_service() -> SampleService:
    """获取申样服务实例"""
    supabase = get_db_client()
    return SampleService(supabase)