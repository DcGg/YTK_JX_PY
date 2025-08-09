"""商品服务

实现商品的CRUD操作、搜索、分类管理等功能。

Author: 云推客严选开发团队
Date: 2024
"""

import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from loguru import logger
from supabase import Client

from ..core.database import get_db_client
from ..models.product import (
    Product, ProductCreate, ProductUpdate, ProductResponse,
    ProductListResponse, ProductSearch, ProductStatistics,
    ProductStatus, ProductCategory
)
from ..models.common import (
    ResponseModel, PaginationParams, PaginationResponse
)


class ProductService:
    """商品服务类
    
    提供商品相关的所有业务功能。
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    async def create_product(
        self, 
        product_data: ProductCreate,
        merchant_id: str
    ) -> ResponseModel[Product]:
        """创建商品
        
        Args:
            product_data: 商品创建数据
            merchant_id: 商家ID
            
        Returns:
            ResponseModel[Product]: 创建结果
        """
        try:
            # 生成商品ID
            product_id = str(uuid.uuid4())
            
            # 构造商品数据
            db_product_data = {
                "id": product_id,
                "merchant_id": merchant_id,
                "name": product_data.name,
                "description": product_data.description,
                "category": product_data.category.value,
                "brand": product_data.brand,
                "model": product_data.model,
                "price": float(product_data.price),
                "cost_price": float(product_data.cost_price) if product_data.cost_price else None,
                "market_price": float(product_data.market_price) if product_data.market_price else None,
                "stock_quantity": product_data.stock_quantity,
                "min_order_quantity": product_data.min_order_quantity,
                "max_order_quantity": product_data.max_order_quantity,
                "unit": product_data.unit,
                "weight": float(product_data.weight) if product_data.weight else None,
                "dimensions": product_data.dimensions,
                "images": [img.dict() for img in product_data.images] if product_data.images else [],
                "specifications": [spec.dict() for spec in product_data.specifications] if product_data.specifications else [],
                "tags": product_data.tags or [],
                "status": product_data.status.value,
                "is_featured": product_data.is_featured,
                "sort_order": product_data.sort_order,
                "seo_title": product_data.seo_title,
                "seo_description": product_data.seo_description,
                "seo_keywords": product_data.seo_keywords,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 插入商品数据
            result = self.supabase.table("products").insert(db_product_data).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="商品创建失败",
                    data=None
                )
            
            # 转换为Product模型
            product = Product(**result.data[0])
            
            logger.info(f"商品创建成功: {product.id}")
            return ResponseModel(
                success=True,
                message="商品创建成功",
                data=product
            )
            
        except Exception as e:
            logger.error(f"创建商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"商品创建失败: {str(e)}",
                data=None
            )
    
    async def get_product_by_id(
        self, 
        product_id: str,
        include_merchant: bool = False
    ) -> ResponseModel[ProductResponse]:
        """根据ID获取商品
        
        Args:
            product_id: 商品ID
            include_merchant: 是否包含商家信息
            
        Returns:
            ResponseModel[ProductResponse]: 商品信息
        """
        try:
            # 构建查询
            query = self.supabase.table("products").select("*")
            
            if include_merchant:
                query = query.select(
                    "*, merchant:users!products_merchant_id_fkey(id, nickname, avatar_url, phone)"
                )
            
            result = query.eq("id", product_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="商品不存在",
                    data=None
                )
            
            product_data = result.data[0]
            
            # 构造响应数据
            if include_merchant and "merchant" in product_data:
                merchant_info = product_data.pop("merchant")
                product_response = ProductResponse(
                    **product_data,
                    merchant_info=merchant_info
                )
            else:
                product_response = ProductResponse(**product_data)
            
            return ResponseModel(
                success=True,
                message="获取商品成功",
                data=product_response
            )
            
        except Exception as e:
            logger.error(f"获取商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取商品失败: {str(e)}",
                data=None
            )
    
    async def update_product(
        self, 
        product_id: str, 
        update_data: ProductUpdate,
        merchant_id: str
    ) -> ResponseModel[Product]:
        """更新商品
        
        Args:
            product_id: 商品ID
            update_data: 更新数据
            merchant_id: 商家ID
            
        Returns:
            ResponseModel[Product]: 更新结果
        """
        try:
            # 检查商品是否存在且属于该商家
            existing_result = self.supabase.table("products").select("id, merchant_id").eq(
                "id", product_id
            ).eq("merchant_id", merchant_id).execute()
            
            if not existing_result.data:
                return ResponseModel(
                    success=False,
                    message="商品不存在或无权限修改",
                    data=None
                )
            
            # 构造更新数据
            db_update_data = update_data.dict(exclude_unset=True)
            
            # 处理特殊字段
            if "price" in db_update_data:
                db_update_data["price"] = float(db_update_data["price"])
            if "cost_price" in db_update_data and db_update_data["cost_price"]:
                db_update_data["cost_price"] = float(db_update_data["cost_price"])
            if "market_price" in db_update_data and db_update_data["market_price"]:
                db_update_data["market_price"] = float(db_update_data["market_price"])
            if "weight" in db_update_data and db_update_data["weight"]:
                db_update_data["weight"] = float(db_update_data["weight"])
            
            # 处理枚举字段
            if "category" in db_update_data:
                db_update_data["category"] = db_update_data["category"].value
            if "status" in db_update_data:
                db_update_data["status"] = db_update_data["status"].value
            
            # 处理复杂字段
            if "images" in db_update_data and db_update_data["images"]:
                db_update_data["images"] = [img.dict() for img in db_update_data["images"]]
            if "specifications" in db_update_data and db_update_data["specifications"]:
                db_update_data["specifications"] = [spec.dict() for spec in db_update_data["specifications"]]
            
            db_update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # 更新商品
            result = self.supabase.table("products").update(
                db_update_data
            ).eq("id", product_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="商品更新失败",
                    data=None
                )
            
            product = Product(**result.data[0])
            
            logger.info(f"商品更新成功: {product_id}")
            return ResponseModel(
                success=True,
                message="商品更新成功",
                data=product
            )
            
        except Exception as e:
            logger.error(f"更新商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"商品更新失败: {str(e)}",
                data=None
            )
    
    async def delete_product(
        self, 
        product_id: str,
        merchant_id: str
    ) -> ResponseModel[bool]:
        """删除商品
        
        Args:
            product_id: 商品ID
            merchant_id: 商家ID
            
        Returns:
            ResponseModel[bool]: 删除结果
        """
        try:
            # 检查商品是否存在且属于该商家
            existing_result = self.supabase.table("products").select("id").eq(
                "id", product_id
            ).eq("merchant_id", merchant_id).execute()
            
            if not existing_result.data:
                return ResponseModel(
                    success=False,
                    message="商品不存在或无权限删除",
                    data=False
                )
            
            # 软删除：更新状态为已删除
            result = self.supabase.table("products").update({
                "status": ProductStatus.DELETED.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", product_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="商品删除失败",
                    data=False
                )
            
            logger.info(f"商品删除成功: {product_id}")
            return ResponseModel(
                success=True,
                message="商品删除成功",
                data=True
            )
            
        except Exception as e:
            logger.error(f"删除商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"商品删除失败: {str(e)}",
                data=False
            )
    
    async def search_products(
        self, 
        search_params: ProductSearch,
        pagination: PaginationParams
    ) -> ResponseModel[ProductListResponse]:
        """搜索商品
        
        Args:
            search_params: 搜索参数
            pagination: 分页参数
            
        Returns:
            ResponseModel[ProductListResponse]: 搜索结果
        """
        try:
            # 构建查询
            query = self.supabase.table("products").select(
                "*, merchant:users!products_merchant_id_fkey(id, nickname, avatar_url)",
                count="exact"
            )
            
            # 基础过滤条件
            query = query.neq("status", ProductStatus.DELETED.value)
            
            # 关键词搜索
            if search_params.keyword:
                # 这里使用简单的文本搜索，实际项目中可以使用全文搜索
                query = query.or_(
                    f"name.ilike.%{search_params.keyword}%,"
                    f"description.ilike.%{search_params.keyword}%,"
                    f"brand.ilike.%{search_params.keyword}%"
                )
            
            # 分类过滤
            if search_params.category:
                query = query.eq("category", search_params.category.value)
            
            # 商家过滤
            if search_params.merchant_id:
                query = query.eq("merchant_id", search_params.merchant_id)
            
            # 状态过滤
            if search_params.status:
                query = query.eq("status", search_params.status.value)
            
            # 价格范围过滤
            if search_params.min_price is not None:
                query = query.gte("price", search_params.min_price)
            if search_params.max_price is not None:
                query = query.lte("price", search_params.max_price)
            
            # 标签过滤
            if search_params.tags:
                for tag in search_params.tags:
                    query = query.contains("tags", [tag])
            
            # 是否精选
            if search_params.is_featured is not None:
                query = query.eq("is_featured", search_params.is_featured)
            
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
            products = []
            for item in result.data:
                merchant_info = item.pop("merchant", None)
                product_response = ProductResponse(
                    **item,
                    merchant_info=merchant_info
                )
                products.append(product_response)
            
            # 分页信息
            total = result.count or 0
            pagination_response = PaginationResponse(
                page=pagination.page,
                page_size=pagination.page_size,
                total=total,
                pages=(total + pagination.page_size - 1) // pagination.page_size
            )
            
            list_response = ProductListResponse(
                items=products,
                pagination=pagination_response
            )
            
            return ResponseModel(
                success=True,
                message="搜索商品成功",
                data=list_response
            )
            
        except Exception as e:
            logger.error(f"搜索商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"搜索商品失败: {str(e)}",
                data=None
            )
    
    async def get_merchant_products(
        self, 
        merchant_id: str,
        pagination: PaginationParams,
        status: Optional[ProductStatus] = None
    ) -> ResponseModel[ProductListResponse]:
        """获取商家商品列表
        
        Args:
            merchant_id: 商家ID
            pagination: 分页参数
            status: 商品状态过滤
            
        Returns:
            ResponseModel[ProductListResponse]: 商品列表
        """
        try:
            # 构建查询
            query = self.supabase.table("products").select(
                "*", count="exact"
            ).eq("merchant_id", merchant_id)
            
            # 状态过滤
            if status:
                query = query.eq("status", status.value)
            else:
                # 默认不显示已删除的商品
                query = query.neq("status", ProductStatus.DELETED.value)
            
            # 排序
            query = query.order("created_at", desc=True)
            
            # 分页
            offset = (pagination.page - 1) * pagination.page_size
            query = query.range(offset, offset + pagination.page_size - 1)
            
            # 执行查询
            result = query.execute()
            
            # 构造响应数据
            products = [ProductResponse(**item) for item in result.data]
            
            # 分页信息
            total = result.count or 0
            pagination_response = PaginationResponse(
                page=pagination.page,
                page_size=pagination.page_size,
                total=total,
                pages=(total + pagination.page_size - 1) // pagination.page_size
            )
            
            list_response = ProductListResponse(
                items=products,
                pagination=pagination_response
            )
            
            return ResponseModel(
                success=True,
                message="获取商家商品成功",
                data=list_response
            )
            
        except Exception as e:
            logger.error(f"获取商家商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取商家商品失败: {str(e)}",
                data=None
            )
    
    async def update_product_stock(
        self, 
        product_id: str, 
        quantity_change: int,
        merchant_id: str
    ) -> ResponseModel[Product]:
        """更新商品库存
        
        Args:
            product_id: 商品ID
            quantity_change: 库存变化量（正数增加，负数减少）
            merchant_id: 商家ID
            
        Returns:
            ResponseModel[Product]: 更新结果
        """
        try:
            # 获取当前商品信息
            result = self.supabase.table("products").select(
                "id, stock_quantity"
            ).eq("id", product_id).eq("merchant_id", merchant_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="商品不存在或无权限修改",
                    data=None
                )
            
            current_stock = result.data[0]["stock_quantity"]
            new_stock = current_stock + quantity_change
            
            # 检查库存不能为负数
            if new_stock < 0:
                return ResponseModel(
                    success=False,
                    message="库存不足",
                    data=None
                )
            
            # 更新库存
            update_result = self.supabase.table("products").update({
                "stock_quantity": new_stock,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", product_id).execute()
            
            if not update_result.data:
                return ResponseModel(
                    success=False,
                    message="库存更新失败",
                    data=None
                )
            
            product = Product(**update_result.data[0])
            
            logger.info(f"商品库存更新成功: {product_id}, 变化量: {quantity_change}")
            return ResponseModel(
                success=True,
                message="库存更新成功",
                data=product
            )
            
        except Exception as e:
            logger.error(f"更新商品库存异常: {e}")
            return ResponseModel(
                success=False,
                message=f"库存更新失败: {str(e)}",
                data=None
            )
    
    async def get_product_statistics(
        self, 
        merchant_id: Optional[str] = None
    ) -> ResponseModel[ProductStatistics]:
        """获取商品统计信息
        
        Args:
            merchant_id: 商家ID（可选，不传则获取全平台统计）
            
        Returns:
            ResponseModel[ProductStatistics]: 统计信息
        """
        try:
            # 构建基础查询
            base_query = self.supabase.table("products")
            
            if merchant_id:
                base_query = base_query.eq("merchant_id", merchant_id)
            
            # 获取各状态商品数量
            total_result = base_query.select("id", count="exact").neq(
                "status", ProductStatus.DELETED.value
            ).execute()
            
            active_result = base_query.select("id", count="exact").eq(
                "status", ProductStatus.ACTIVE.value
            ).execute()
            
            inactive_result = base_query.select("id", count="exact").eq(
                "status", ProductStatus.INACTIVE.value
            ).execute()
            
            out_of_stock_result = base_query.select("id", count="exact").eq(
                "stock_quantity", 0
            ).neq("status", ProductStatus.DELETED.value).execute()
            
            # 获取分类统计
            category_result = base_query.select(
                "category", count="exact"
            ).neq("status", ProductStatus.DELETED.value).execute()
            
            # 统计各分类数量
            category_stats = {}
            for category in ProductCategory:
                category_count = base_query.select("id", count="exact").eq(
                    "category", category.value
                ).neq("status", ProductStatus.DELETED.value).execute()
                category_stats[category.value] = category_count.count or 0
            
            statistics = ProductStatistics(
                total_products=total_result.count or 0,
                active_products=active_result.count or 0,
                inactive_products=inactive_result.count or 0,
                out_of_stock_products=out_of_stock_result.count or 0,
                category_distribution=category_stats
            )
            
            return ResponseModel(
                success=True,
                message="获取商品统计成功",
                data=statistics
            )
            
        except Exception as e:
            logger.error(f"获取商品统计异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取商品统计失败: {str(e)}",
                data=None
            )
    
    async def batch_update_products(
        self, 
        product_ids: List[str], 
        update_data: Dict[str, Any],
        merchant_id: str
    ) -> ResponseModel[List[Product]]:
        """批量更新商品
        
        Args:
            product_ids: 商品ID列表
            update_data: 更新数据
            merchant_id: 商家ID
            
        Returns:
            ResponseModel[List[Product]]: 更新结果
        """
        try:
            # 检查所有商品是否属于该商家
            check_result = self.supabase.table("products").select("id").eq(
                "merchant_id", merchant_id
            ).in_("id", product_ids).execute()
            
            if len(check_result.data) != len(product_ids):
                return ResponseModel(
                    success=False,
                    message="部分商品不存在或无权限修改",
                    data=None
                )
            
            # 添加更新时间
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # 批量更新
            result = self.supabase.table("products").update(
                update_data
            ).in_("id", product_ids).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="批量更新失败",
                    data=None
                )
            
            products = [Product(**item) for item in result.data]
            
            logger.info(f"批量更新商品成功: {len(products)}个商品")
            return ResponseModel(
                success=True,
                message=f"批量更新成功，共更新{len(products)}个商品",
                data=products
            )
            
        except Exception as e:
            logger.error(f"批量更新商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"批量更新失败: {str(e)}",
                data=None
            )


# 依赖注入函数
def get_product_service() -> ProductService:
    """获取商品服务实例"""
    supabase = get_db_client()
    return ProductService(supabase)