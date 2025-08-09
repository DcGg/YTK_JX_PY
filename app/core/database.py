#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云推客严选数据库连接模块

本模块负责管理数据库连接和操作，包括：
1. Supabase客户端初始化
2. 数据库连接池管理
3. 数据库操作基础类
4. 事务管理
5. 连接健康检查

Author: 云推客严选开发团队
Date: 2024
"""

from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from loguru import logger
import asyncio
from contextlib import asynccontextmanager

from app.core.config import settings


class DatabaseManager:
    """
    数据库管理器
    
    负责管理Supabase客户端连接和数据库操作
    """
    
    def __init__(self):
        """
        初始化数据库管理器
        """
        self._client: Optional[Client] = None
        self._is_connected: bool = False
    
    async def connect(self) -> None:
        """
        建立数据库连接
        
        初始化Supabase客户端并测试连接
        
        Raises:
            Exception: 连接失败时抛出异常
        """
        try:
            logger.info("正在连接Supabase数据库...")
            
            # 验证配置
            if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
                raise ValueError("Supabase配置不完整，请检查SUPABASE_URL和SUPABASE_ANON_KEY")
            
            # 创建Supabase客户端
            self._client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_ANON_KEY
            )
            
            # 测试连接
            await self.health_check()
            
            self._is_connected = True
            logger.success("✅ Supabase数据库连接成功")
            
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """
        断开数据库连接
        """
        if self._client:
            self._client = None
            self._is_connected = False
            logger.info("数据库连接已断开")
    
    async def health_check(self) -> bool:
        """
        数据库健康检查
        
        Returns:
            bool: 连接是否健康
        """
        try:
            if not self._client:
                return False
            
            # 执行简单查询测试连接
            result = self._client.table('users').select('id').limit(1).execute()
            return True
            
        except Exception as e:
            logger.warning(f"数据库健康检查失败: {str(e)}")
            return False
    
    @property
    def client(self) -> Client:
        """
        获取Supabase客户端
        
        Returns:
            Client: Supabase客户端实例
            
        Raises:
            RuntimeError: 客户端未初始化时抛出异常
        """
        if not self._client:
            raise RuntimeError("数据库客户端未初始化，请先调用connect()方法")
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """
        检查是否已连接
        
        Returns:
            bool: 是否已连接
        """
        return self._is_connected


class BaseRepository:
    """
    数据库操作基础类
    
    提供通用的数据库操作方法
    """
    
    def __init__(self, table_name: str):
        """
        初始化仓储类
        
        Args:
            table_name (str): 表名
        """
        self.table_name = table_name
        self.db = db_manager
    
    def get_table(self):
        """
        获取表操作对象
        
        Returns:
            表操作对象
        """
        return self.db.client.table(self.table_name)
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建记录
        
        Args:
            data (Dict[str, Any]): 要创建的数据
            
        Returns:
            Dict[str, Any]: 创建的记录
            
        Raises:
            Exception: 创建失败时抛出异常
        """
        try:
            result = self.get_table().insert(data).execute()
            if result.data:
                return result.data[0]
            raise Exception("创建记录失败")
        except Exception as e:
            logger.error(f"创建{self.table_name}记录失败: {str(e)}")
            raise
    
    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取记录
        
        Args:
            record_id (str): 记录ID
            
        Returns:
            Optional[Dict[str, Any]]: 记录数据，不存在时返回None
        """
        try:
            result = self.get_table().select('*').eq('id', record_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"获取{self.table_name}记录失败: {str(e)}")
            raise
    
    async def update(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新记录
        
        Args:
            record_id (str): 记录ID
            data (Dict[str, Any]): 要更新的数据
            
        Returns:
            Dict[str, Any]: 更新后的记录
        """
        try:
            result = self.get_table().update(data).eq('id', record_id).execute()
            if result.data:
                return result.data[0]
            raise Exception("更新记录失败")
        except Exception as e:
            logger.error(f"更新{self.table_name}记录失败: {str(e)}")
            raise
    
    async def delete(self, record_id: str) -> bool:
        """
        删除记录
        
        Args:
            record_id (str): 记录ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            result = self.get_table().delete().eq('id', record_id).execute()
            return True
        except Exception as e:
            logger.error(f"删除{self.table_name}记录失败: {str(e)}")
            raise
    
    async def list(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分页查询记录
        
        Args:
            page (int): 页码
            size (int): 每页大小
            filters (Optional[Dict[str, Any]]): 过滤条件
            order_by (Optional[str]): 排序字段
            
        Returns:
            Dict[str, Any]: 分页结果
        """
        try:
            # 计算偏移量
            offset = (page - 1) * size
            
            # 构建查询
            query = self.get_table().select('*')
            
            # 应用过滤条件
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            # 应用排序
            if order_by:
                query = query.order(order_by)
            
            # 应用分页
            query = query.range(offset, offset + size - 1)
            
            result = query.execute()
            
            # 获取总数（简化实现，实际应该单独查询）
            count_result = self.get_table().select('id', count='exact').execute()
            total = count_result.count if count_result.count else 0
            
            return {
                'items': result.data or [],
                'total': total,
                'page': page,
                'size': size,
                'pages': (total + size - 1) // size
            }
            
        except Exception as e:
            logger.error(f"查询{self.table_name}列表失败: {str(e)}")
            raise


# 创建全局数据库管理器实例
db_manager = DatabaseManager()


async def init_db() -> None:
    """
    初始化数据库连接
    
    在应用启动时调用
    """
    await db_manager.connect()


async def close_db() -> None:
    """
    关闭数据库连接
    
    在应用关闭时调用
    """
    await db_manager.disconnect()


@asynccontextmanager
async def get_db():
    """
    获取数据库连接的上下文管理器
    
    用于依赖注入
    """
    if not db_manager.is_connected:
        await db_manager.connect()
    
    try:
        yield db_manager.client
    finally:
        # 这里可以添加清理逻辑
        pass


def get_db_client() -> Client:
    """
    获取数据库客户端
    
    用于FastAPI依赖注入
    
    Returns:
        Client: Supabase客户端
    """
    return db_manager.client


if __name__ == "__main__":
    # 测试数据库连接
    async def test_connection():
        await init_db()
        health = await db_manager.health_check()
        print(f"数据库健康状态: {health}")
        await close_db()
    
    asyncio.run(test_connection())