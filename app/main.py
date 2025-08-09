"""云推客严选 FastAPI 应用主文件

这是云推客严选后端API的主入口文件，负责：
1. 创建FastAPI应用实例
2. 配置CORS中间件
3. 注册所有API路由
4. 配置异常处理
5. 生成API文档

Author: AI Assistant
Date: 2024
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.core.config import settings
from app.api import (
    auth,
    products,
    orders,
    collections,
    relationships,
    samples,
    health
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title="云推客严选 API",
    description="云推客严选平台后端API服务，提供用户认证、商品管理、订单管理、货盘管理、达人管理、申样管理等功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理器"""
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    logger.error(f"请求验证异常: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求参数验证失败",
            "data": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "data": None
        }
    )

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    logger.info("云推客严选 API 服务启动中...")
    logger.info(f"环境: {settings.ENVIRONMENT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info("API 服务启动完成")

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的操作"""
    logger.info("云推客严选 API 服务正在关闭...")
    logger.info("API 服务已关闭")

# 注册API路由
app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["用户认证"])
app.include_router(products.router, prefix="/api/v1/products", tags=["商品管理"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["订单管理"])
app.include_router(collections.router, prefix="/api/v1/collections", tags=["货盘管理"])
app.include_router(relationships.router, prefix="/api/v1/relationships", tags=["达人管理"])
app.include_router(samples.router, prefix="/api/v1/samples", tags=["申样管理"])

# 根路径
@app.get("/", tags=["根路径"])
async def root():
    """根路径欢迎信息"""
    return {
        "success": True,
        "message": "欢迎使用云推客严选 API",
        "data": {
            "service": "云推客严选 API",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )