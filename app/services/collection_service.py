"""货盘服务

实现货盘的CRUD操作、商品管理、数据统计等功能。

Author: 云推客严选开发团队
Date: 2024
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from loguru import logger
from supabase import Client

from ..core.database import get_db_client
from ..models.collection import (
    Collection, CollectionCreate, CollectionUpdate, CollectionResponse,
    CollectionDetailResponse, CollectionListResponse, CollectionSearch,
    CollectionStatistics, CollectionStatus, CollectionType,
    CollectionItem, CollectionItemCreate, CollectionItemUpdate,
    CollectionItemResponse, CollectionBatchOperation,
    CollectionShareRequest, CollectionShareResponse
)
from ..models.common import (
    ResponseModel, PaginationParams, PaginationResponse
)
from ..services.product_service import get_product_service


class CollectionService:
    """货盘服务类
    
    提供货盘相关的所有业务功能。
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.product_service = get_product_service()
    
    async def create_collection(
        self, 
        collection_data: CollectionCreate,
        creator_id: str
    ) -> ResponseModel[Collection]:
        """创建货盘
        
        Args:
            collection_data: 货盘创建数据
            creator_id: 创建者ID
            
        Returns:
            ResponseModel[Collection]: 创建结果
        """
        try:
            # 生成货盘ID
            collection_id = str(uuid.uuid4())
            
            # 构造货盘数据
            db_collection_data = {
                "id": collection_id,
                "name": collection_data.name,
                "description": collection_data.description,
                "type": collection_data.type.value,
                "status": CollectionStatus.ACTIVE.value,
                "creator_id": creator_id,
                "cover_image": collection_data.cover_image,
                "tags": collection_data.tags or [],
                "is_public": collection_data.is_public,
                "sort_order": collection_data.sort_order or 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 插入货盘
            result = self.supabase.table("collections").insert(db_collection_data).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="货盘创建失败",
                    data=None
                )
            
            collection = Collection(**result.data[0])
            
            logger.info(f"货盘创建成功: {collection.name}")
            return ResponseModel(
                success=True,
                message="货盘创建成功",
                data=collection
            )
            
        except Exception as e:
            logger.error(f"创建货盘异常: {e}")
            return ResponseModel(
                success=False,
                message=f"货盘创建失败: {str(e)}",
                data=None
            )
    
    async def get_collection_by_id(
        self, 
        collection_id: str,
        user_id: str,
        include_items: bool = True
    ) -> ResponseModel[CollectionDetailResponse]:
        """根据ID获取货盘详情
        
        Args:
            collection_id: 货盘ID
            user_id: 用户ID
            include_items: 是否包含货盘商品
            
        Returns:
            ResponseModel[CollectionDetailResponse]: 货盘详情
        """
        try:
            # 获取货盘基本信息
            collection_result = self.supabase.table("collections").select(
                "*, creator:users!collections_creator_id_fkey(id, nickname, avatar_url)"
            ).eq("id", collection_id).execute()
            
            if not collection_result.data:
                return ResponseModel(
                    success=False,
                    message="货盘不存在",
                    data=None
                )
            
            collection_data = collection_result.data[0]
            
            # 权限检查：私有货盘只有创建者可以查看
            if not collection_data["is_public"] and collection_data["creator_id"] != user_id:
                return ResponseModel(
                    success=False,
                    message="无权限查看此货盘",
                    data=None
                )
            
            # 获取货盘商品
            collection_items = []
            if include_items:
                items_result = self.supabase.table("collection_items").select(
                    "*, product:products!collection_items_product_id_fkey(*)"
                ).eq("collection_id", collection_id).order("sort_order").execute()
                
                for item_data in items_result.data:
                    product_data = item_data.pop("product", None)
                    collection_item = CollectionItemResponse(
                        **item_data,
                        product=product_data
                    )
                    collection_items.append(collection_item)
            
            # 构造响应数据
            creator_info = collection_data.pop("creator", None)
            collection_detail = CollectionDetailResponse(
                **collection_data,
                items=collection_items,
                creator_info=creator_info,
                item_count=len(collection_items)
            )
            
            return ResponseModel(
                success=True,
                message="获取货盘详情成功",
                data=collection_detail
            )
            
        except Exception as e:
            logger.error(f"获取货盘详情异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取货盘详情失败: {str(e)}",
                data=None
            )
    
    async def update_collection(
        self, 
        collection_id: str, 
        update_data: CollectionUpdate,
        user_id: str
    ) -> ResponseModel[Collection]:
        """更新货盘信息
        
        Args:
            collection_id: 货盘ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            ResponseModel[Collection]: 更新结果
        """
        try:
            # 检查货盘是否存在且有权限
            existing_result = self.supabase.table("collections").select(
                "id, creator_id"
            ).eq("id", collection_id).execute()
            
            if not existing_result.data:
                return ResponseModel(
                    success=False,
                    message="货盘不存在",
                    data=None
                )
            
            collection_info = existing_result.data[0]
            
            # 权限检查：只有创建者可以更新
            if collection_info["creator_id"] != user_id:
                return ResponseModel(
                    success=False,
                    message="无权限更新此货盘",
                    data=None
                )
            
            # 构造更新数据
            db_update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 只更新提供的字段
            if update_data.name is not None:
                db_update_data["name"] = update_data.name
            if update_data.description is not None:
                db_update_data["description"] = update_data.description
            if update_data.cover_image is not None:
                db_update_data["cover_image"] = update_data.cover_image
            if update_data.tags is not None:
                db_update_data["tags"] = update_data.tags
            if update_data.is_public is not None:
                db_update_data["is_public"] = update_data.is_public
            if update_data.status is not None:
                db_update_data["status"] = update_data.status.value
            if update_data.sort_order is not None:
                db_update_data["sort_order"] = update_data.sort_order
            
            # 更新货盘
            result = self.supabase.table("collections").update(
                db_update_data
            ).eq("id", collection_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="货盘更新失败",
                    data=None
                )
            
            collection = Collection(**result.data[0])
            
            logger.info(f"货盘更新成功: {collection_id}")
            return ResponseModel(
                success=True,
                message="货盘更新成功",
                data=collection
            )
            
        except Exception as e:
            logger.error(f"更新货盘异常: {e}")
            return ResponseModel(
                success=False,
                message=f"货盘更新失败: {str(e)}",
                data=None
            )
    
    async def delete_collection(
        self, 
        collection_id: str,
        user_id: str
    ) -> ResponseModel[bool]:
        """删除货盘
        
        Args:
            collection_id: 货盘ID
            user_id: 用户ID
            
        Returns:
            ResponseModel[bool]: 删除结果
        """
        try:
            # 检查货盘是否存在且有权限
            existing_result = self.supabase.table("collections").select(
                "id, creator_id"
            ).eq("id", collection_id).execute()
            
            if not existing_result.data:
                return ResponseModel(
                    success=False,
                    message="货盘不存在",
                    data=False
                )
            
            collection_info = existing_result.data[0]
            
            # 权限检查：只有创建者可以删除
            if collection_info["creator_id"] != user_id:
                return ResponseModel(
                    success=False,
                    message="无权限删除此货盘",
                    data=False
                )
            
            # 软删除：更新状态为已删除
            result = self.supabase.table("collections").update({
                "status": CollectionStatus.DELETED.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", collection_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="货盘删除失败",
                    data=False
                )
            
            logger.info(f"货盘删除成功: {collection_id}")
            return ResponseModel(
                success=True,
                message="货盘删除成功",
                data=True
            )
            
        except Exception as e:
            logger.error(f"删除货盘异常: {e}")
            return ResponseModel(
                success=False,
                message=f"货盘删除失败: {str(e)}",
                data=False
            )
    
    async def add_item_to_collection(
        self, 
        collection_id: str,
        item_data: CollectionItemCreate,
        user_id: str
    ) -> ResponseModel[CollectionItem]:
        """向货盘添加商品
        
        Args:
            collection_id: 货盘ID
            item_data: 商品数据
            user_id: 用户ID
            
        Returns:
            ResponseModel[CollectionItem]: 添加结果
        """
        try:
            # 检查货盘权限
            collection_result = self.supabase.table("collections").select(
                "id, creator_id, status"
            ).eq("id", collection_id).execute()
            
            if not collection_result.data:
                return ResponseModel(
                    success=False,
                    message="货盘不存在",
                    data=None
                )
            
            collection_info = collection_result.data[0]
            
            # 权限检查
            if collection_info["creator_id"] != user_id:
                return ResponseModel(
                    success=False,
                    message="无权限操作此货盘",
                    data=None
                )
            
            # 状态检查
            if collection_info["status"] != CollectionStatus.ACTIVE.value:
                return ResponseModel(
                    success=False,
                    message="货盘状态不允许添加商品",
                    data=None
                )
            
            # 验证商品是否存在
            product_result = await self.product_service.get_product_by_id(item_data.product_id)
            if not product_result.success:
                return ResponseModel(
                    success=False,
                    message="商品不存在",
                    data=None
                )
            
            # 检查商品是否已在货盘中
            existing_item = self.supabase.table("collection_items").select(
                "id"
            ).eq("collection_id", collection_id).eq(
                "product_id", item_data.product_id
            ).execute()
            
            if existing_item.data:
                return ResponseModel(
                    success=False,
                    message="商品已在货盘中",
                    data=None
                )
            
            # 生成商品项ID
            item_id = str(uuid.uuid4())
            
            # 构造商品项数据
            db_item_data = {
                "id": item_id,
                "collection_id": collection_id,
                "product_id": item_data.product_id,
                "sort_order": item_data.sort_order or 0,
                "notes": item_data.notes,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 插入商品项
            result = self.supabase.table("collection_items").insert(db_item_data).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="添加商品到货盘失败",
                    data=None
                )
            
            collection_item = CollectionItem(**result.data[0])
            
            # 更新货盘的更新时间
            self.supabase.table("collections").update({
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", collection_id).execute()
            
            logger.info(f"商品添加到货盘成功: {item_data.product_id} -> {collection_id}")
            return ResponseModel(
                success=True,
                message="商品添加到货盘成功",
                data=collection_item
            )
            
        except Exception as e:
            logger.error(f"添加商品到货盘异常: {e}")
            return ResponseModel(
                success=False,
                message=f"添加商品到货盘失败: {str(e)}",
                data=None
            )
    
    async def remove_item_from_collection(
        self, 
        collection_id: str,
        item_id: str,
        user_id: str
    ) -> ResponseModel[bool]:
        """从货盘移除商品
        
        Args:
            collection_id: 货盘ID
            item_id: 商品项ID
            user_id: 用户ID
            
        Returns:
            ResponseModel[bool]: 移除结果
        """
        try:
            # 检查货盘权限
            collection_result = self.supabase.table("collections").select(
                "id, creator_id"
            ).eq("id", collection_id).execute()
            
            if not collection_result.data:
                return ResponseModel(
                    success=False,
                    message="货盘不存在",
                    data=False
                )
            
            collection_info = collection_result.data[0]
            
            # 权限检查
            if collection_info["creator_id"] != user_id:
                return ResponseModel(
                    success=False,
                    message="无权限操作此货盘",
                    data=False
                )
            
            # 删除商品项
            result = self.supabase.table("collection_items").delete().eq(
                "id", item_id
            ).eq("collection_id", collection_id).execute()
            
            if not result.data:
                return ResponseModel(
                    success=False,
                    message="商品项不存在或移除失败",
                    data=False
                )
            
            # 更新货盘的更新时间
            self.supabase.table("collections").update({
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", collection_id).execute()
            
            logger.info(f"商品从货盘移除成功: {item_id}")
            return ResponseModel(
                success=True,
                message="商品从货盘移除成功",
                data=True
            )
            
        except Exception as e:
            logger.error(f"从货盘移除商品异常: {e}")
            return ResponseModel(
                success=False,
                message=f"从货盘移除商品失败: {str(e)}",
                data=False
            )
    
    async def search_collections(
        self, 
        search_params: CollectionSearch,
        pagination: PaginationParams,
        user_id: str
    ) -> ResponseModel[CollectionListResponse]:
        """搜索货盘
        
        Args:
            search_params: 搜索参数
            pagination: 分页参数
            user_id: 用户ID
            
        Returns:
            ResponseModel[CollectionListResponse]: 搜索结果
        """
        try:
            # 构建查询
            query = self.supabase.table("collections").select(
                "*, creator:users!collections_creator_id_fkey(id, nickname, avatar_url)",
                count="exact"
            )
            
            # 基础过滤：排除已删除的货盘
            query = query.neq("status", CollectionStatus.DELETED.value)
            
            # 权限过滤：公开货盘或自己创建的货盘
            if search_params.creator_id:
                # 如果指定了创建者，只查看该创建者的货盘
                query = query.eq("creator_id", search_params.creator_id)
                # 如果不是查看自己的，只能看公开的
                if search_params.creator_id != user_id:
                    query = query.eq("is_public", True)
            else:
                # 查看公开货盘或自己创建的货盘
                query = query.or_(f"is_public.eq.true,creator_id.eq.{user_id}")
            
            # 名称搜索
            if search_params.name:
                query = query.ilike("name", f"%{search_params.name}%")
            
            # 类型过滤
            if search_params.type:
                query = query.eq("type", search_params.type.value)
            
            # 状态过滤
            if search_params.status:
                query = query.eq("status", search_params.status.value)
            
            # 标签过滤
            if search_params.tags:
                for tag in search_params.tags:
                    query = query.contains("tags", [tag])
            
            # 排序
            if search_params.sort_by:
                if search_params.sort_order == "desc":
                    query = query.order(search_params.sort_by, desc=True)
                else:
                    query = query.order(search_params.sort_by)
            else:
                # 默认按更新时间倒序
                query = query.order("updated_at", desc=True)
            
            # 分页
            offset = (pagination.page - 1) * pagination.page_size
            query = query.range(offset, offset + pagination.page_size - 1)
            
            # 执行查询
            result = query.execute()
            
            # 构造响应数据
            collections = []
            for item in result.data:
                creator_info = item.pop("creator", None)
                
                # 获取货盘商品数量
                item_count_result = self.supabase.table("collection_items").select(
                    "id", count="exact"
                ).eq("collection_id", item["id"]).execute()
                
                collection_response = CollectionResponse(
                    **item,
                    creator_info=creator_info,
                    item_count=item_count_result.count or 0
                )
                collections.append(collection_response)
            
            # 分页信息
            total = result.count or 0
            pagination_response = PaginationResponse(
                page=pagination.page,
                page_size=pagination.page_size,
                total=total,
                pages=(total + pagination.page_size - 1) // pagination.page_size
            )
            
            list_response = CollectionListResponse(
                items=collections,
                pagination=pagination_response
            )
            
            return ResponseModel(
                success=True,
                message="搜索货盘成功",
                data=list_response
            )
            
        except Exception as e:
            logger.error(f"搜索货盘异常: {e}")
            return ResponseModel(
                success=False,
                message=f"搜索货盘失败: {str(e)}",
                data=None
            )
    
    async def get_collection_statistics(
        self, 
        user_id: str,
        days: int = 30
    ) -> ResponseModel[CollectionStatistics]:
        """获取货盘统计信息
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            ResponseModel[CollectionStatistics]: 统计信息
        """
        try:
            # 计算时间范围
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 获取用户的货盘统计
            total_result = self.supabase.table("collections").select(
                "*", count="exact"
            ).eq("creator_id", user_id).neq(
                "status", CollectionStatus.DELETED.value
            ).execute()
            
            active_result = self.supabase.table("collections").select(
                "*", count="exact"
            ).eq("creator_id", user_id).eq(
                "status", CollectionStatus.ACTIVE.value
            ).execute()
            
            public_result = self.supabase.table("collections").select(
                "*", count="exact"
            ).eq("creator_id", user_id).eq(
                "is_public", True
            ).neq("status", CollectionStatus.DELETED.value).execute()
            
            # 获取最近创建的货盘数量
            recent_result = self.supabase.table("collections").select(
                "*", count="exact"
            ).eq("creator_id", user_id).gte(
                "created_at", start_date.isoformat()
            ).neq("status", CollectionStatus.DELETED.value).execute()
            
            # 获取货盘中的商品总数
            total_items_result = self.supabase.table("collection_items").select(
                "collection_id", count="exact"
            ).in_(
                "collection_id", 
                [col["id"] for col in total_result.data]
            ).execute()
            
            statistics = CollectionStatistics(
                total_collections=total_result.count or 0,
                active_collections=active_result.count or 0,
                public_collections=public_result.count or 0,
                recent_collections=recent_result.count or 0,
                total_items=total_items_result.count or 0
            )
            
            return ResponseModel(
                success=True,
                message="获取货盘统计成功",
                data=statistics
            )
            
        except Exception as e:
            logger.error(f"获取货盘统计异常: {e}")
            return ResponseModel(
                success=False,
                message=f"获取货盘统计失败: {str(e)}",
                data=None
            )


# 依赖注入函数
def get_collection_service() -> CollectionService:
    """获取货盘服务实例"""
    supabase = get_db_client()
    return CollectionService(supabase)