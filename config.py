import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用基础配置
    app_name: str = "MCP Cloud Studio"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 数据库配置
    database_url: str = "sqlite:///./mcp_studio.db"
    
    # JWT安全配置
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 验证码配置
    captcha_length: int = 4
    captcha_width: int = 120
    captcha_height: int = 40
    
    # MCP配置
    mcp_workspace_dir: str = "./mcp_workspace"
    max_mcp_tools_per_user: int = 10
    max_file_size_mb: int = 10
    
    # WebSocket配置
    ws_heartbeat_interval: int = 30
    ws_timeout: int = 300
    
    # Redis配置（用于Celery任务队列）
    redis_url: str = "redis://localhost:6379/0"
    
    # 监控配置
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    # 文件上传配置
    upload_dir: str = "./uploads"
    allowed_file_extensions: list = [".py", ".txt", ".json", ".yaml", ".yml"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 全局设置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.mcp_workspace_dir, exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)