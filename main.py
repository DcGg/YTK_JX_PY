"""云推客严选后端API主应用

基于FastAPI框架的云推客严选后端服务，提供用户认证、商品管理、
订单管理、货盘管理、达人管理、申样管理等核心功能。

Author: 云推客严选开发团队
Date: 2024
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger
import uvicorn

from app.api import api_router
from app.core.config import settings
from app.core.database import get_db_client
from app.models.common import ResponseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理
    
    在应用启动和关闭时执行必要的初始化和清理工作。
    """
    # 启动时的初始化工作
    logger.info("🚀 云推客严选后端服务启动中...")
    
    # 初始化数据库连接
    try:
        from app.core.database import db_manager
        await db_manager.connect()
        supabase = get_db_client()
        # 简单的连接测试
        result = supabase.table("users").select("count", count="exact").limit(1).execute()
        logger.info(f"✅ Supabase数据库连接成功，用户表记录数: {result.count}")
    except Exception as e:
        logger.error(f"❌ Supabase数据库连接失败: {e}")
        # 在开发环境中，即使数据库连接失败也继续启动
        if settings.DEBUG:
            logger.warning("⚠️ 开发模式：忽略数据库连接错误，继续启动服务")
        else:
            raise
    
    logger.info("✅ 云推客严选后端服务启动完成")
    
    yield
    
    # 关闭时的清理工作
    logger.info("🛑 云推客严选后端服务正在关闭...")
    logger.info("✅ 云推客严选后端服务已关闭")


# 创建FastAPI应用实例
app = FastAPI(
    title="云推客严选后端API",
    description="""云推客严选后端服务API文档
    
    ## 功能模块
    
    * **健康检查** - 系统健康状态检查
    * **用户认证** - 用户注册、登录、JWT令牌管理
    * **用户管理** - 用户信息管理、角色权限控制
    * **商品管理** - 商品CRUD、搜索、分类管理
    * **订单管理** - 订单查询、统计、状态更新
    * **货盘管理** - 货盘创建、商品管理、数据统计
    * **达人管理** - 达人信息、绑定关系、数据分析
    * **申样管理** - 申样请求、状态跟踪、审核处理
    
    ## 认证方式
    
    API使用JWT Bearer Token进行认证，请在请求头中添加：
    ```
    Authorization: Bearer <your_token>
    ```
    
    ## 错误码说明
    
    * **200** - 请求成功
    * **400** - 请求参数错误
    * **401** - 未授权访问
    * **403** - 权限不足
    * **404** - 资源不存在
    * **422** - 请求数据验证失败
    * **429** - 请求频率限制
    * **500** - 服务器内部错误
    """,
    version="1.0.0",
    contact={
        "name": "云推客严选开发团队",
        "email": "dev@yuntuke.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "健康检查",
            "description": "系统健康状态检查接口",
        },
        {
            "name": "用户认证",
            "description": "用户注册、登录、JWT令牌管理",
        },
        {
            "name": "用户管理",
            "description": "用户信息管理、角色权限控制",
        },
        {
            "name": "商品管理",
            "description": "商品CRUD、搜索、分类管理",
        },
        {
            "name": "订单管理",
            "description": "订单查询、统计、状态更新",
        },
        {
            "name": "货盘管理",
            "description": "货盘创建、商品管理、数据统计",
        },
        {
            "name": "达人管理",
            "description": "达人信息、绑定关系、数据分析",
        },
        {
            "name": "申样管理",
            "description": "申样请求、状态跟踪、审核处理",
        },
    ],
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)


# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
    ],
    expose_headers=["X-Total-Count", "X-Page-Count"],
)


# 配置可信主机中间件（生产环境）
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(
        f"📥 {request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'} - "
        f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
    )
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    
    # 记录响应信息
    logger.info(
        f"📤 {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    # 添加处理时间到响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    logger.warning(
        f"HTTP异常: {exc.status_code} - {exc.detail} - "
        f"Path: {request.url.path} - "
        f"Method: {request.method}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseModel(
            success=False,
            message=exc.detail,
            data=None
        ).dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """请求验证异常处理器"""
    logger.warning(
        f"请求验证失败: {exc.errors()} - "
        f"Path: {request.url.path} - "
        f"Method: {request.method}"
    )
    
    # 格式化验证错误信息
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_details.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=422,
        content=ResponseModel(
            success=False,
            message="请求数据验证失败",
            data={"errors": error_details}
        ).dict()
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(
    request: Request, 
    exc: StarletteHTTPException
) -> JSONResponse:
    """Starlette HTTP异常处理器"""
    logger.error(
        f"Starlette异常: {exc.status_code} - {exc.detail} - "
        f"Path: {request.url.path} - "
        f"Method: {request.method}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseModel(
            success=False,
            message=str(exc.detail),
            data=None
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger.error(
        f"未处理异常: {type(exc).__name__}: {str(exc)} - "
        f"Path: {request.url.path} - "
        f"Method: {request.method}",
        exc_info=True
    )
    
    # 生产环境不暴露详细错误信息
    if settings.ENVIRONMENT == "production":
        message = "服务器内部错误"
    else:
        message = f"{type(exc).__name__}: {str(exc)}"
    
    return JSONResponse(
        status_code=500,
        content=ResponseModel(
            success=False,
            message=message,
            data=None
        ).dict()
    )


# 注册API路由
app.include_router(api_router, prefix="/api/v1")


# 根路径重定向到API文档
@app.get("/", include_in_schema=False)
async def root():
    """根路径，重定向到API文档"""
    return {
        "message": "欢迎使用云推客严选后端API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/api/v1/health"
    }


# 开发环境启动配置
if __name__ == "__main__":
    # 配置日志
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=9001,
        reload=True,
        log_level="info",
        access_log=True
    )