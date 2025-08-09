"""订单服务

实现订单的CRUD操作、状态管理、支付处理等功能。

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
from ..models.order import (
    Order, OrderCreate, OrderUpdate, OrderResponse,
    OrderListResponse, OrderSearch, OrderStatistics,
    OrderStatus, PaymentMethod, PaymentStatus,
    OrderItem, OrderItemCreate, ShippingAddress,
    PaymentRequest, PaymentResponse
)
from ..models.common import (
    ResponseModel, PaginationParams, PaginationResponse
)
from ..services.product_service import get_product_service


class OrderService:
    """订单服务类
    
    提供订单相关的所有业务功能。
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.product_service = get_product_service()
    
    async def create_order(
        self, 
        order_data: OrderCreate,
        buyer_id: str
    ) -> ResponseModel[Order]:
        """创建订单
        
        Args:
            order_data: 订单创建数据
            buyer_id: 买家ID
            
        Returns:
            ResponseModel[Order]: 创建结果
        """
        try:
            # 生成订单ID和订单号
            order_id = str(uuid.uuid4())
            order_number = self._generate_order_number()
            
            # 验证商品信息并计算总价
            total_amount = Decimal('0')
            order_items_data = []
            
            for item in order_data.items:
                # 获取商品信息
                product_result = await self.product_service.get_product_by_id(item.product_id)
                if not product_result.success:
                    return ResponseModel(
                        success=False,
                        message=f"商品 {item.product_id} 不存在",
                        data=None
                    )
                
                product = product_result.data
                
                # 检查库存
                if product.stock_quantity < item.quantity:
                    return ResponseModel(
                        success=False,
                        message=f"商品 {product.name} 库存不足",
                        data=None
                    )
                
                # 检查最小/最大订购量
                if item.quantity < product.min_order_quantity:
                    return ResponseModel(
                        success=False,
                        message=f"商品 {product.name} 最小订购量为 {product.min_order_quantity}",
                        data=None
                    )
                
                if product.max_order_quantity and item.quantity > product.max_order_quantity:
                    return ResponseModel(
                        success=False,
                        message=f"商品 {product.name} 最大订购量为 {product.max_order_quantity}",
                        data=None
                    )
                
                # 计算商品小计
                unit_price = Decimal(str(product.price))
                subtotal = unit_price * item.quantity
                total_amount += subtotal
                
                # 构造订单项数据
                order_item_data = {
                    "id": str(uuid.uuid4()),
                    "order_id": order_id,
                    "product_id": item.product_id,
                    "product_name": product.name,
                    "product_image": product.images[0].url if product.images else None,
                    "unit_price": float(unit_price),
                    "quantity": item.quantity,
                    "subtotal": float(subtotal),
                    "specifications": item.specifications or {},
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                order_items_data.append(order_item_data)
            
            # 构造订单数据
            db_order_data = {
                "id": order_id,
                "order_number": order_number,
                "buyer_id": buyer_id,
                "merchant_id": order_data.merchant_id,
                "total_amount": float(total_amount),
                "shipping_fee": float(order_data.shipping_fee) if order_data.shipping_fee else 0.0,
                "discount_amount": float(order_data.discount_amount) if order_data.discount_amount else 0.0,
                "final_amount": float(total_amount + Decimal(str(order_data.shipping_fee or 0)) - Decimal(str(order_data.discount_amount or 0))),
                "status": OrderStatus.PENDING.value,
                "payment_method": order_data.payment_method.value if order_data.payment_method else None,
                "payment_status": PaymentStatus.PENDING.value,
                "shipping_address": order_data.shipping_address.dict() if order_data.shipping_address else None,
                "notes": order_data.notes,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 开始事务：创建订单和订单项
            # 插入订单
            order_result = self.supabase.table("orders").insert(db_order_data).execute()
            
            if not order_result.data:
                return ResponseModel(
                    success=False,
                    message="订单创建失败",
                    data=None
                )
            
            # 插入订单项
            if order_items_data:
                items_result = self.supabase.table("order_items").insert(order_items_data).execute()
                
                if not items_result.data:
                    # 如果订单项创建失败，需要删除已创建的订单
                    self.supabase.table("orders").delete().eq("id", order_id).execute()
                    return ResponseModel(
                        success=False,
                        message="订单项创建失败",
                        data=None
                    )
            
            # 更新商品库存
            for item in order_data.items:
                await self.product_service.update_product_stock(
                    product_id=item.product_id,
                    quantity_change=-item.quantity,
                    merchant_id=order_data.merchant_id
                )
            
            # 转换为Order模型
            order = Order(**order_result.data[0])
            
            logger.info(f"订单创建成功: {order.order_number}")
            return ResponseModel(
                success=True,
                message="订单创建成功",
                data=order
            )
            
        except Exception as e:
            logger.error(f"创建订单异常: {e}")
            return ResponseModel(
                success=False,
                message=f"订单创建失败: {str(e)}",
                data=None
            )
    
    async def get_order_by_id(
        self, 
        order_id: str,
        user_id: str,
        include_items: bool = True
    ) -> ResponseModel[OrderResponse]:
        """根据ID获取订单
        
        Args:
            order_id: 订单ID
            user_id: 用户ID
            include_items: 是否包含订单项
            
        Returns:
            ResponseModel[OrderResponse]: 订单信息
        """
        try:
            # 构建查询
            query = self.supabase.table("orders").select("*")
            
            # 权限检查：只能查看自己的订单（买家或卖家）
            query = query.eq("id", order_id).or_(
                f"buyer_id.eq.{user_id},merchant_id.eq.{user_id}"
            )
            
            result = query.execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="订单不存在或无权限查看",
                    data=None
                )
            
            order_data = result.data[0]
            
            # 获取订单项
            order_items = []
            if include_items:
                items_result = self.supabase.table("order_items").select(
                    "*"
                ).eq("order_id", order_id).execute()
                
                order_items = [OrderItem(**item) for item in items_result.data]
            
            # 构造响应数据
            order_response = OrderResponse(
                **order_data,
                items=order_items
            )
            
            return ResponseModel(
                success=True,
                message="获取订单成功",
                data=order_response
            )
            
        except Exception as e:
            logger.error(f"获取订单异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取订单失败: {str(e)}",
                data=None
            )
    
    async def update_order_status(
        self, 
        order_id: str, 
        new_status: OrderStatus,
        user_id: str,
        notes: Optional[str] = None
    ) -> ResponseModel[Order]:
        """更新订单状态
        
        Args:
            order_id: 订单ID
            new_status: 新状态
            user_id: 操作用户ID
            notes: 备注
            
        Returns:
            ResponseModel[Order]: 更新结果
        """
        try:
            # 检查订单是否存在且有权限操作
            existing_result = self.supabase.table("orders").select(
                "id, status, buyer_id, merchant_id"
            ).eq("id", order_id).execute()
            
            if not existing_result.data:
                return ResponseModel(
                    success=False,
                    message="订单不存在",
                    data=None
                )
            
            order_info = existing_result.data[0]
            current_status = OrderStatus(order_info["status"])
            
            # 权限检查
            if user_id not in [order_info["buyer_id"], order_info["merchant_id"]]:
                return ResponseModel(
                    success=False,
                    message="无权限操作此订单",
                    data=None
                )
            
            # 状态转换验证
            if not self._is_valid_status_transition(current_status, new_status):
                return ResponseModel(
                    success=False,
                    message=f"无法从 {current_status.value} 状态转换到 {new_status.value}",
                    data=None
                )
            
            # 构造更新数据
            update_data = {
                "status": new_status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 根据状态设置特殊字段
            if new_status == OrderStatus.CONFIRMED:
                update_data["confirmed_at"] = datetime.utcnow().isoformat()
            elif new_status == OrderStatus.SHIPPED:
                update_data["shipped_at"] = datetime.utcnow().isoformat()
            elif new_status == OrderStatus.DELIVERED:
                update_data["delivered_at"] = datetime.utcnow().isoformat()
            elif new_status == OrderStatus.CANCELLED:
                update_data["cancelled_at"] = datetime.utcnow().isoformat()
                # 取消订单时恢复库存
                await self._restore_order_stock(order_id)
            
            if notes:
                update_data["notes"] = notes
            
            # 更新订单
            result = self.supabase.table("orders").update(
                update_data
            ).eq("id", order_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="订单状态更新失败",
                    data=None
                )
            
            order = Order(**result.data[0])
            
            logger.info(f"订单状态更新成功: {order_id} -> {new_status.value}")
            return ResponseModel(
                success=True,
                message="订单状态更新成功",
                data=order
            )
            
        except Exception as e:
            logger.error(f"更新订单状态异常: {e}")
            return ResponseModel(
                success=False,
                message=f"订单状态更新失败: {str(e)}",
                data=None
            )
    
    async def search_orders(
        self, 
        search_params: OrderSearch,
        pagination: PaginationParams,
        user_id: str
    ) -> ResponseModel[OrderListResponse]:
        """搜索订单
        
        Args:
            search_params: 搜索参数
            pagination: 分页参数
            user_id: 用户ID
            
        Returns:
            ResponseModel[OrderListResponse]: 搜索结果
        """
        try:
            # 构建查询
            query = self.supabase.table("orders").select(
                "*, buyer:users!orders_buyer_id_fkey(id, nickname, avatar_url), "
                "merchant:users!orders_merchant_id_fkey(id, nickname, avatar_url)",
                count="exact"
            )
            
            # 权限过滤：只能查看自己相关的订单
            if search_params.buyer_id:
                query = query.eq("buyer_id", search_params.buyer_id)
            elif search_params.merchant_id:
                query = query.eq("merchant_id", search_params.merchant_id)
            else:
                # 如果没有指定买家或商家，则查看用户自己的订单
                query = query.or_(f"buyer_id.eq.{user_id},merchant_id.eq.{user_id}")
            
            # 订单号搜索
            if search_params.order_number:
                query = query.ilike("order_number", f"%{search_params.order_number}%")
            
            # 状态过滤
            if search_params.status:
                query = query.eq("status", search_params.status.value)
            
            # 支付状态过滤
            if search_params.payment_status:
                query = query.eq("payment_status", search_params.payment_status.value)
            
            # 时间范围过滤
            if search_params.start_date:
                query = query.gte("created_at", search_params.start_date.isoformat())
            if search_params.end_date:
                query = query.lte("created_at", search_params.end_date.isoformat())
            
            # 金额范围过滤
            if search_params.min_amount is not None:
                query = query.gte("final_amount", search_params.min_amount)
            if search_params.max_amount is not None:
                query = query.lte("final_amount", search_params.max_amount)
            
            # 排序
            if search_params.sort_by:
                if search_params.sort_order == "desc":
                    query = query.order(search_params.sort_by, desc=True)
                else:
                    query = query.order(search_params.sort_by)
            else:
                # 默认按创建时间倒序
                query = query.order("created_at", desc=True)
            
            # 分页
            offset = (pagination.page - 1) * pagination.page_size
            query = query.range(offset, offset + pagination.page_size - 1)
            
            # 执行查询
            result = query.execute()
            
            # 构造响应数据
            orders = []
            for item in result.data:
                buyer_info = item.pop("buyer", None)
                merchant_info = item.pop("merchant", None)
                
                # 获取订单项（简化版，只获取基本信息）
                items_result = self.supabase.table("order_items").select(
                    "id, product_id, product_name, quantity, unit_price, subtotal"
                ).eq("order_id", item["id"]).execute()
                
                order_items = [OrderItem(**order_item) for order_item in items_result.data]
                
                order_response = OrderResponse(
                    **item,
                    items=order_items,
                    buyer_info=buyer_info,
                    merchant_info=merchant_info
                )
                orders.append(order_response)
            
            # 分页信息
            total = result.count or 0
            pagination_response = PaginationResponse(
                page=pagination.page,
                page_size=pagination.page_size,
                total=total,
                pages=(total + pagination.page_size - 1) // pagination.page_size
            )
            
            list_response = OrderListResponse(
                items=orders,
                pagination=pagination_response
            )
            
            return ResponseModel(
                success=True,
                message="搜索订单成功",
                data=list_response
            )
            
        except Exception as e:
            logger.error(f"搜索订单异常: {e}")
            return ResponseModel(
                success=False,
                message=f"搜索订单失败: {str(e)}",
                data=None
            )
    
    async def get_order_statistics(
        self, 
        user_id: str,
        days: int = 30
    ) -> ResponseModel[OrderStatistics]:
        """获取订单统计信息
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            ResponseModel[OrderStatistics]: 统计信息
        """
        try:
            # 计算时间范围
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 构建基础查询
            base_query = self.supabase.table("orders").select(
                "*", count="exact"
            ).or_(f"buyer_id.eq.{user_id},merchant_id.eq.{user_id}")
            
            # 时间范围过滤
            time_filtered_query = base_query.gte(
                "created_at", start_date.isoformat()
            ).lte("created_at", end_date.isoformat())
            
            # 获取各状态订单数量
            total_result = time_filtered_query.execute()
            
            pending_result = time_filtered_query.eq(
                "status", OrderStatus.PENDING.value
            ).execute()
            
            confirmed_result = time_filtered_query.eq(
                "status", OrderStatus.CONFIRMED.value
            ).execute()
            
            shipped_result = time_filtered_query.eq(
                "status", OrderStatus.SHIPPED.value
            ).execute()
            
            delivered_result = time_filtered_query.eq(
                "status", OrderStatus.DELIVERED.value
            ).execute()
            
            cancelled_result = time_filtered_query.eq(
                "status", OrderStatus.CANCELLED.value
            ).execute()
            
            # 计算总金额
            total_amount = sum(
                float(order.get("final_amount", 0)) 
                for order in total_result.data
            )
            
            # 计算平均订单金额
            avg_order_amount = (
                total_amount / len(total_result.data) 
                if total_result.data else 0
            )
            
            statistics = OrderStatistics(
                total_orders=total_result.count or 0,
                pending_orders=pending_result.count or 0,
                confirmed_orders=confirmed_result.count or 0,
                shipped_orders=shipped_result.count or 0,
                delivered_orders=delivered_result.count or 0,
                cancelled_orders=cancelled_result.count or 0,
                total_amount=total_amount,
                avg_order_amount=avg_order_amount
            )
            
            return ResponseModel(
                success=True,
                message="获取订单统计成功",
                data=statistics
            )
            
        except Exception as e:
            logger.error(f"获取订单统计异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取订单统计失败: {str(e)}",
                data=None
            )
    
    def _generate_order_number(self) -> str:
        """生成订单号"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = str(uuid.uuid4()).replace("-", "")[:6].upper()
        return f"YTK{timestamp}{random_suffix}"
    
    def _is_valid_status_transition(
        self, 
        current_status: OrderStatus, 
        new_status: OrderStatus
    ) -> bool:
        """验证订单状态转换是否有效"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [],  # 已完成订单不能再转换
            OrderStatus.CANCELLED: []   # 已取消订单不能再转换
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    async def _restore_order_stock(self, order_id: str):
        """恢复订单库存"""
        try:
            # 获取订单项
            items_result = self.supabase.table("order_items").select(
                "product_id, quantity"
            ).eq("order_id", order_id).execute()
            
            # 恢复每个商品的库存
            for item in items_result.data:
                await self.product_service.update_product_stock(
                    product_id=item["product_id"],
                    quantity_change=item["quantity"],
                    merchant_id=""  # 这里需要获取商家ID，简化处理
                )
                
        except Exception as e:
            logger.error(f"恢复订单库存异常: {e}")


# 依赖注入函数
def get_order_service() -> OrderService:
    """获取订单服务实例"""
    supabase = get_db_client()
    return OrderService(supabase)