"""通用数据模型

定义平台通用的基础数据模型，包括分页、响应格式等。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field
from uuid import UUID

# 泛型类型变量
DataType = TypeVar('DataType')


class BaseModel(PydanticBaseModel):
    """基础模型类
    
    所有数据模型的基类，提供通用配置和方法。
    """
    
    class Config:
        """Pydantic配置"""
        # 允许使用字段别名
        allow_population_by_field_name = True
        # 验证赋值
        validate_assignment = True
        # 使用枚举值
        use_enum_values = True
        # JSON编码器配置
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class TimestampMixin(BaseModel):
    """时间戳混入类
    
    为模型添加创建时间和更新时间字段。
    """
    
    created_at: Optional[datetime] = Field(
        None,
        description="创建时间",
        example="2024-01-01T00:00:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="更新时间",
        example="2024-01-01T00:00:00Z"
    )


class UUIDMixin(BaseModel):
    """UUID混入类
    
    为模型添加UUID主键字段。
    """
    
    id: Optional[UUID] = Field(
        None,
        description="唯一标识符",
        example="123e4567-e89b-12d3-a456-426614174000"
    )


class PaginationParams(BaseModel):
    """分页参数模型
    
    用于API请求的分页参数。
    """
    
    page: int = Field(
        1,
        ge=1,
        description="页码，从1开始",
        example=1
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="每页数量，最大100",
        example=20
    )
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """获取限制数量"""
        return self.page_size


class PaginationResponse(BaseModel, Generic[DataType]):
    """分页响应模型
    
    用于API响应的分页数据格式。
    """
    
    items: List[DataType] = Field(
        description="数据列表"
    )
    total: int = Field(
        description="总数量",
        example=100
    )
    page: int = Field(
        description="当前页码",
        example=1
    )
    page_size: int = Field(
        description="每页数量",
        example=20
    )
    total_pages: int = Field(
        description="总页数",
        example=5
    )
    has_next: bool = Field(
        description="是否有下一页",
        example=True
    )
    has_prev: bool = Field(
        description="是否有上一页",
        example=False
    )
    
    @classmethod
    def create(
        cls,
        items: List[DataType],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginationResponse[DataType]":
        """创建分页响应
        
        Args:
            items: 数据列表
            total: 总数量
            page: 当前页码
            page_size: 每页数量
            
        Returns:
            分页响应对象
        """
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )


class ResponseModel(BaseModel, Generic[DataType]):
    """通用响应模型
    
    标准化API响应格式。
    """
    
    success: bool = Field(
        description="请求是否成功",
        example=True
    )
    message: str = Field(
        description="响应消息",
        example="操作成功"
    )
    data: Optional[DataType] = Field(
        None,
        description="响应数据"
    )
    code: int = Field(
        200,
        description="响应代码",
        example=200
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="响应时间戳",
        example="2024-01-01T00:00:00Z"
    )


class SuccessResponse(ResponseModel[DataType]):
    """成功响应模型"""
    
    success: bool = Field(True, description="请求成功")
    message: str = Field("操作成功", description="成功消息")
    code: int = Field(200, description="成功代码")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    
    success: bool = Field(
        False,
        description="请求失败"
    )
    message: str = Field(
        description="错误消息",
        example="请求失败"
    )
    error_code: Optional[str] = Field(
        None,
        description="错误代码",
        example="VALIDATION_ERROR"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="错误详情"
    )
    code: int = Field(
        400,
        description="HTTP状态码",
        example=400
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="错误时间戳",
        example="2024-01-01T00:00:00Z"
    )


class SearchParams(BaseModel):
    """搜索参数模型"""
    
    keyword: Optional[str] = Field(
        None,
        description="搜索关键词",
        example="商品名称"
    )
    category: Optional[str] = Field(
        None,
        description="分类筛选",
        example="美妆护肤"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="排序字段",
        example="created_at"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="排序方向",
        example="desc",
        pattern="^(asc|desc)$"
    )


class FilterParams(BaseModel):
    """筛选参数模型"""
    
    status: Optional[str] = Field(
        None,
        description="状态筛选",
        example="active"
    )
    platform: Optional[str] = Field(
        None,
        description="平台筛选",
        example="wechat"
    )
    date_from: Optional[datetime] = Field(
        None,
        description="开始日期",
        example="2024-01-01T00:00:00Z"
    )
    date_to: Optional[datetime] = Field(
        None,
        description="结束日期",
        example="2024-12-31T23:59:59Z"
    )


class StatisticsModel(BaseModel):
    """统计数据模型"""
    
    total_count: int = Field(
        description="总数量",
        example=100
    )
    active_count: int = Field(
        description="活跃数量",
        example=80
    )
    growth_rate: float = Field(
        description="增长率",
        example=0.15
    )
    period: str = Field(
        description="统计周期",
        example="monthly"
    )


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    
    status: str = Field(
        "healthy",
        description="服务状态",
        example="healthy"
    )
    version: str = Field(
        description="版本号",
        example="1.0.0"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="检查时间"
    )
    services: Dict[str, str] = Field(
        description="依赖服务状态",
        example={
            "database": "connected",
            "redis": "connected",
            "supabase": "connected"
        }
    )