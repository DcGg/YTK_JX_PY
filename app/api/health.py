"""健康检查API

提供系统健康状态检查接口。

Author: 云推客严选开发团队
Date: 2024
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from ..core.database import get_db_client
from ..models.common import HealthCheckResponse, ResponseModel

router = APIRouter()


@router.get("/", response_model=ResponseModel[HealthCheckResponse])
async def health_check(
    supabase=Depends(get_db_client)
) -> ResponseModel[HealthCheckResponse]:
    """系统健康检查
    
    检查系统各组件的运行状态。
    
    Returns:
        ResponseModel[HealthCheckResponse]: 健康检查结果
    """
    try:
        # 检查数据库连接
        db_status = "healthy"
        db_message = "数据库连接正常"
        
        try:
            # 执行简单查询测试数据库连接
            result = supabase.table("users").select("count", count="exact").limit(1).execute()
            if result.count is None:
                db_status = "unhealthy"
                db_message = "数据库查询失败"
        except Exception as e:
            db_status = "unhealthy"
            db_message = f"数据库连接失败: {str(e)}"
            logger.error(f"数据库健康检查失败: {e}")
        
        # 系统整体状态
        overall_status = "healthy" if db_status == "healthy" else "unhealthy"
        
        health_data = HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            services={
                "database": {
                    "status": db_status,
                    "message": db_message
                },
                "api": {
                    "status": "healthy",
                    "message": "API服务正常"
                }
            }
        )
        
        return ResponseModel(
            success=True,
            message="健康检查完成",
            data=health_data
        )
        
    except Exception as e:
        logger.error(f"健康检查异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get("/ping")
async def ping() -> Dict[str, Any]:
    """简单的ping检查
    
    Returns:
        Dict[str, Any]: ping响应
    """
    return {
        "message": "pong",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "ok"
    }


@router.get("/version")
async def get_version() -> Dict[str, str]:
    """获取API版本信息
    
    Returns:
        Dict[str, str]: 版本信息
    """
    return {
        "version": "1.0.0",
        "name": "云推客严选API",
        "description": "云推客严选后端API服务"
    }