#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云推客严选应用配置模块

本模块负责管理应用的所有配置信息，包括：
1. 数据库连接配置
2. JWT认证配置
3. 微信API配置
4. Redis缓存配置
5. 应用运行环境配置

使用pydantic-settings进行配置管理，支持从环境变量读取配置

Author: 云推客严选开发团队
Date: 2024
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    应用配置类
    
    使用pydantic-settings管理配置，支持从环境变量读取
    配置优先级：环境变量 > .env文件 > 默认值
    """
    
    # 应用基础配置
    APP_NAME: str = "云推客严选API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=True, description="调试模式")
    ENVIRONMENT: str = Field(default="development", description="运行环境")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8000, description="服务器端口")
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"], 
        description="允许的主机列表"
    )
    
    # Supabase数据库配置
    SUPABASE_URL: str = Field(
        default="", 
        description="Supabase项目URL"
    )
    SUPABASE_ANON_KEY: str = Field(
        default="", 
        description="Supabase匿名密钥"
    )
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="", 
        description="Supabase服务角色密钥"
    )
    
    # 数据库连接配置
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="数据库连接URL"
    )
    
    # JWT认证配置
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT密钥"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT加密算法"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="访问令牌过期时间（分钟）"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="刷新令牌过期时间（天）"
    )
    
    # 微信API配置
    WECHAT_APP_ID: str = Field(
        default="",
        description="微信小程序AppID"
    )
    WECHAT_APP_SECRET: str = Field(
        default="",
        description="微信小程序AppSecret"
    )
    WECHAT_MCH_ID: str = Field(
        default="",
        description="微信商户号"
    )
    WECHAT_API_KEY: str = Field(
        default="",
        description="微信API密钥"
    )
    WECHAT_NOTIFY_URL: str = Field(
        default="",
        description="微信支付回调URL"
    )
    WECHAT_API_BASE_URL: str = Field(
        default="https://api.weixin.qq.com",
        description="微信API基础URL"
    )
    
    # Redis缓存配置
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        description="Redis密码"
    )
    CACHE_EXPIRE_SECONDS: int = Field(
        default=3600,
        description="缓存过期时间（秒）"
    )
    
    # 文件上传配置
    UPLOAD_MAX_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="文件上传最大大小（字节）"
    )
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov"],
        description="允许上传的文件扩展名"
    )
    
    # 日志配置
    LOG_LEVEL: str = Field(
        default="INFO",
        description="日志级别"
    )
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="日志文件路径"
    )
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = Field(
        default=20,
        description="默认分页大小"
    )
    MAX_PAGE_SIZE: int = Field(
        default=100,
        description="最大分页大小"
    )
    
    # 业务配置
    DEFAULT_COMMISSION_RATE: float = Field(
        default=0.05,
        description="默认佣金比例"
    )
    MAX_COMMISSION_RATE: float = Field(
        default=0.50,
        description="最大佣金比例"
    )
    
    class Config:
        """
        Pydantic配置类
        """
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    def get_database_url(self) -> str:
        """
        获取数据库连接URL
        
        优先使用DATABASE_URL，如果没有则从Supabase配置构建
        
        Returns:
            str: 数据库连接URL
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
            
        if self.SUPABASE_URL:
            # 从Supabase URL构建PostgreSQL连接URL
            # 注意：这里需要根据实际的Supabase配置调整
            return f"postgresql://postgres:[password]@[host]:5432/postgres"
            
        raise ValueError("数据库配置不完整，请设置DATABASE_URL或Supabase配置")
    
    def is_development(self) -> bool:
        """
        判断是否为开发环境
        
        Returns:
            bool: 是否为开发环境
        """
        return self.ENVIRONMENT.lower() in ["development", "dev"]
    
    def is_production(self) -> bool:
        """
        判断是否为生产环境
        
        Returns:
            bool: 是否为生产环境
        """
        return self.ENVIRONMENT.lower() in ["production", "prod"]


# 创建全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """
    获取应用配置实例
    
    Returns:
        Settings: 配置实例
    """
    return settings


# 配置验证函数
def validate_config() -> bool:
    """
    验证配置的完整性
    
    检查必要的配置项是否已设置
    
    Returns:
        bool: 配置是否有效
    """
    required_configs = [
        "SECRET_KEY",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY"
    ]
    
    missing_configs = []
    for config in required_configs:
        if not getattr(settings, config):
            missing_configs.append(config)
    
    if missing_configs:
        print(f"❌ 缺少必要配置: {', '.join(missing_configs)}")
        return False
    
    print("✅ 配置验证通过")
    return True


if __name__ == "__main__":
    # 配置测试
    print(f"应用名称: {settings.APP_NAME}")
    print(f"运行环境: {settings.ENVIRONMENT}")
    print(f"调试模式: {settings.DEBUG}")
    validate_config()