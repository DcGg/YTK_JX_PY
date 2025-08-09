"""订单数据模型

定义订单相关的数据模型，包括订单信息、订单项、状态、支付等。

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from decimal import Decimal
from datetime import datetime
from pydantic import Field, validator
from uuid import UUID

from .common import BaseModel, TimestampMixin, UUIDMixin


class OrderStatus(str, Enum):
    """订单状态枚举"""
    
    PENDING = "pending"              # 待付款
    PAID = "paid"                    # 已付款
    CONFIRMED = "confirmed"          # 已确认
    SHIPPED = "shipped"              # 已发货
    DELIVERED = "delivered"          # 已送达
    COMPLETED = "completed"          # 已完成
    CANCELLED = "cancelled"          # 已取消
    REFUNDED = "refunded"            # 已退款
    RETURNED = "returned"            # 已退货


class PaymentMethod(str, Enum):
    """支付方式枚举"""
    
    WECHAT_PAY = "wechat_pay"        # 微信支付
    ALIPAY = "alipay"                # 支付宝
    BANK_CARD = "bank_card"          # 银行卡
    BALANCE = "balance"              # 余额支付
    OTHER = "other"                  # 其他


class PaymentStatus(str, Enum):
    """支付状态枚举"""
    
    PENDING = "pending"              # 待支付
    SUCCESS = "success"              # 支付成功
    FAILED = "failed"                # 支付失败
    CANCELLED = "cancelled"          # 已取消
    REFUNDED = "refunded"            # 已退款


class ShippingAddress(BaseModel):
    """收货地址模型"""
    
    recipient_name: str = Field(
        description="收货人姓名",
        min_length=1,
        max_length=50,
        example="张三"
    )
    phone: str = Field(
        description="联系电话",
        pattern=r"^1[3-9]\d{9}$",
        example="13800138000"
    )
    province: str = Field(
        description="省份",
        example="北京市"
    )
    city: str = Field(
        description="城市",
        example="北京市"
    )
    district: str = Field(
        description="区县",
        example="朝阳区"
    )
    street: str = Field(
        description="详细地址",
        min_length=1,
        max_length=200,
        example="三里屯街道工体北路8号"
    )
    postal_code: Optional[str] = Field(
        None,
        description="邮政编码",
        pattern=r"^\d{6}$",
        example="100027"
    )
    is_default: bool = Field(
        False,
        description="是否为默认地址",
        example=False
    )


class OrderItemBase(BaseModel):
    """订单项基础模型"""
    
    product_id: UUID = Field(
        description="商品ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    product_title: str = Field(
        description="商品标题",
        example="高端护肤精华液 50ml"
    )
    product_image: Optional[str] = Field(
        None,
        description="商品图片",
        example="https://example.com/product/image.jpg"
    )
    specification: Optional[str] = Field(
        None,
        description="商品规格",
        example="红色/50ml"
    )
    unit_price: Decimal = Field(
        description="单价",
        gt=0,
        decimal_places=2,
        example=199.00
    )
    quantity: int = Field(
        description="数量",
        gt=0,
        example=2
    )
    commission_rate: Decimal = Field(
        description="佣金比例",
        ge=0,
        le=1,
        decimal_places=4,
        example=0.15
    )
    
    @validator('quantity')
    def validate_quantity(cls, v):
        """验证数量"""
        if v <= 0:
            raise ValueError('数量必须大于0')
        return v


class OrderItemCreate(OrderItemBase):
    """创建订单项模型"""
    pass


class OrderItem(UUIDMixin, OrderItemBase, TimestampMixin):
    """订单项完整模型"""
    
    order_id: UUID = Field(
        description="订单ID",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    subtotal: Decimal = Field(
        description="小计金额",
        decimal_places=2,
        example=398.00
    )
    commission_amount: Decimal = Field(
        description="佣金金额",
        decimal_places=2,
        example=59.70
    )
    
    class Config:
        """Pydantic配置"""
        from_attributes = True


class OrderBase(BaseModel):
    """订单基础模型"""
    
    buyer_id: UUID = Field(
        description="买家ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    merchant_id: UUID = Field(
        description="商家ID",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    referrer_id: Optional[UUID] = Field(
        None,
        description="推荐人ID（团长或达人）",
        example="123e4567-e89b-12d3-a456-426614174002"
    )
    order_number: str = Field(
        description="订单号",
        example="YTK202401010001"
    )
    items: List[OrderItemCreate] = Field(
        description="订单项列表",
        min_items=1
    )
    shipping_address: ShippingAddress = Field(
        description="收货地址"
    )
    remark: Optional[str] = Field(
        None,
        description="订单备注",
        max_length=500,
        example="请尽快发货"
    )
    
    @validator('items')
    def validate_items(cls, v):
        """验证订单项"""
        if not v:
            raise ValueError('订单项不能为空')
        return v


class OrderCreate(OrderBase):
    """创建订单模型"""
    
    @validator('order_number')
    def validate_order_number(cls, v):
        """验证订单号格式"""
        if not v or len(v) < 10:
            raise ValueError('订单号格式不正确')
        return v


class OrderUpdate(BaseModel):
    """更新订单模型"""
    
    status: Optional[OrderStatus] = Field(
        None,
        description="订单状态"
    )
    shipping_address: Optional[ShippingAddress] = Field(
        None,
        description="收货地址"
    )
    remark: Optional[str] = Field(
        None,
        description="订单备注",
        max_length=500
    )
    tracking_number: Optional[str] = Field(
        None,
        description="快递单号",
        example="SF1234567890"
    )
    shipping_company: Optional[str] = Field(
        None,
        description="快递公司",
        example="顺丰速运"
    )


class Order(UUIDMixin, TimestampMixin):
    """订单完整模型"""
    
    buyer_id: UUID = Field(
        description="买家ID"
    )
    merchant_id: UUID = Field(
        description="商家ID"
    )
    referrer_id: Optional[UUID] = Field(
        None,
        description="推荐人ID"
    )
    order_number: str = Field(
        description="订单号"
    )
    status: OrderStatus = Field(
        OrderStatus.PENDING,
        description="订单状态"
    )
    total_amount: Decimal = Field(
        description="订单总金额",
        decimal_places=2,
        example=398.00
    )
    discount_amount: Decimal = Field(
        0,
        description="优惠金额",
        decimal_places=2,
        example=0.00
    )
    shipping_fee: Decimal = Field(
        0,
        description="运费",
        decimal_places=2,
        example=10.00
    )
    final_amount: Decimal = Field(
        description="实付金额",
        decimal_places=2,
        example=408.00
    )
    commission_total: Decimal = Field(
        0,
        description="总佣金",
        decimal_places=2,
        example=59.70
    )
    shipping_address: ShippingAddress = Field(
        description="收货地址"
    )
    remark: Optional[str] = Field(
        None,
        description="订单备注"
    )
    payment_method: Optional[PaymentMethod] = Field(
        None,
        description="支付方式"
    )
    payment_status: PaymentStatus = Field(
        PaymentStatus.PENDING,
        description="支付状态"
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="支付时间"
    )
    shipped_at: Optional[datetime] = Field(
        None,
        description="发货时间"
    )
    delivered_at: Optional[datetime] = Field(
        None,
        description="送达时间"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="完成时间"
    )
    tracking_number: Optional[str] = Field(
        None,
        description="快递单号"
    )
    shipping_company: Optional[str] = Field(
        None,
        description="快递公司"
    )
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "buyer_id": "123e4567-e89b-12d3-a456-426614174001",
                "merchant_id": "123e4567-e89b-12d3-a456-426614174002",
                "order_number": "YTK202401010001",
                "status": "pending",
                "total_amount": 398.00,
                "final_amount": 408.00,
                "payment_status": "pending",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class OrderResponse(Order):
    """订单响应模型
    
    用于API响应，包含关联数据。
    """
    
    items: List[OrderItem] = Field(
        description="订单项列表"
    )
    buyer_name: Optional[str] = Field(
        None,
        description="买家姓名",
        example="张三"
    )
    merchant_name: Optional[str] = Field(
        None,
        description="商家名称",
        example="云推客科技"
    )
    referrer_name: Optional[str] = Field(
        None,
        description="推荐人姓名",
        example="李四"
    )
    referrer_type: Optional[str] = Field(
        None,
        description="推荐人类型",
        example="leader"
    )
    can_cancel: bool = Field(
        True,
        description="是否可以取消",
        example=True
    )
    can_pay: bool = Field(
        True,
        description="是否可以支付",
        example=True
    )
    can_confirm: bool = Field(
        False,
        description="是否可以确认收货",
        example=False
    )


class OrderListResponse(BaseModel):
    """订单列表响应模型"""
    
    orders: List[OrderResponse] = Field(
        description="订单列表"
    )
    total: int = Field(
        description="总数量",
        example=100
    )
    page: int = Field(
        description="当前页码",
        example=1
    )
    size: int = Field(
        description="每页数量",
        example=20
    )
    pages: int = Field(
        description="总页数",
        example=5
    )


class OrderSearch(BaseModel):
    """订单搜索模型"""
    
    order_number: Optional[str] = Field(
        None,
        description="订单号",
        example="YTK202401010001"
    )
    buyer_id: Optional[UUID] = Field(
        None,
        description="买家ID"
    )
    merchant_id: Optional[UUID] = Field(
        None,
        description="商家ID"
    )
    referrer_id: Optional[UUID] = Field(
        None,
        description="推荐人ID"
    )
    status: Optional[OrderStatus] = Field(
        None,
        description="订单状态"
    )
    payment_status: Optional[PaymentStatus] = Field(
        None,
        description="支付状态"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="开始日期"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="结束日期"
    )
    min_amount: Optional[Decimal] = Field(
        None,
        description="最小金额",
        ge=0
    )
    max_amount: Optional[Decimal] = Field(
        None,
        description="最大金额",
        ge=0
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="排序字段",
        example="created_at"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="排序方向",
        example="desc"
    )


class OrderStatistics(BaseModel):
    """订单统计模型"""
    
    total_orders: int = Field(
        description="订单总数",
        example=1000
    )
    pending_orders: int = Field(
        description="待付款订单数",
        example=50
    )
    paid_orders: int = Field(
        description="已付款订单数",
        example=800
    )
    completed_orders: int = Field(
        description="已完成订单数",
        example=700
    )
    cancelled_orders: int = Field(
        description="已取消订单数",
        example=100
    )
    total_amount: Decimal = Field(
        description="订单总金额",
        example=199800.00
    )
    total_commission: Decimal = Field(
        description="总佣金",
        example=29970.00
    )
    average_order_value: Decimal = Field(
        description="平均订单价值",
        example=199.80
    )
    conversion_rate: float = Field(
        description="转化率",
        example=0.85
    )
    daily_orders: List[Dict[str, Any]] = Field(
        description="每日订单统计",
        example=[
            {"date": "2024-01-01", "count": 10, "amount": 1998.00},
            {"date": "2024-01-02", "count": 15, "amount": 2997.00}
        ]
    )


class PaymentRequest(BaseModel):
    """支付请求模型"""
    
    order_id: UUID = Field(
        description="订单ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    payment_method: PaymentMethod = Field(
        description="支付方式",
        example=PaymentMethod.WECHAT_PAY
    )
    return_url: Optional[str] = Field(
        None,
        description="支付成功返回URL",
        example="https://example.com/payment/success"
    )


class PaymentResponse(BaseModel):
    """支付响应模型"""
    
    payment_id: str = Field(
        description="支付ID",
        example="pay_123456789"
    )
    payment_url: Optional[str] = Field(
        None,
        description="支付链接",
        example="https://pay.example.com/pay?id=123456789"
    )
    qr_code: Optional[str] = Field(
        None,
        description="支付二维码",
        example="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    )
    expires_at: datetime = Field(
        description="过期时间",
        example="2024-01-01T01:00:00Z"
    )