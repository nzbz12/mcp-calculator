from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator
from database import MCPToolStatus

# 用户相关模型
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    captcha_session_id: str
    captcha_code: str
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric with optional underscores and hyphens')
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username must be between 3 and 50 characters')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserLogin(BaseModel):
    username: str
    password: str
    captcha_session_id: str
    captcha_code: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# 认证相关模型
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class CaptchaResponse(BaseModel):
    session_id: str
    image_data: str

# MCP工具相关模型
class MCPToolBase(BaseModel):
    name: str
    description: Optional[str] = None
    endpoint_url: str = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjE2MSwiYWdlbnRJZCI6MTcwMSwiZW5kcG9pbnRJZCI6ImFnZW50XzE3MDEiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzU1MjQzNzMzfQ._iaI8kpPu2UpOFsjW3IIEKB1ABXh9VOKcNcojXL2eWfsx7DGwAH6FLqu00n3X3DmOOLFHOFkdtHHB4dfkWiGhA"
    
    @validator('name')
    def name_valid(cls, v):
        if len(v) < 1 or len(v) > 100:
            raise ValueError('Tool name must be between 1 and 100 characters')
        return v

class MCPToolCreate(MCPToolBase):
    pass

class MCPToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    endpoint_url: Optional[str] = None

class MCPToolResponse(MCPToolBase):
    id: int
    status: MCPToolStatus
    original_filename: str
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_started_at: Optional[datetime]
    last_stopped_at: Optional[datetime]
    total_runs: int
    total_runtime_seconds: int
    process_id: Optional[int]
    
    class Config:
        from_attributes = True

class MCPToolListResponse(BaseModel):
    tools: List[MCPToolResponse]
    total: int
    page: int
    page_size: int

# 系统日志模型
class SystemLogResponse(BaseModel):
    id: int
    level: str
    message: str
    module: Optional[str]
    user_id: Optional[int]
    mcp_tool_id: Optional[int]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# 统计信息模型
class UserStatsResponse(BaseModel):
    total_tools: int
    running_tools: int
    total_runs: int
    total_runtime_hours: float

class AdminStatsResponse(BaseModel):
    total_users: int
    total_tools: int
    running_tools: int
    total_system_logs: int

# 文件上传响应
class FileUploadResponse(BaseModel):
    filename: str
    size: int
    content_preview: str

# WebSocket消息模型
class WSMessage(BaseModel):
    type: str  # "status_update", "log", "error"
    tool_id: Optional[int] = None
    data: dict

# 通用响应模型
class MessageResponse(BaseModel):
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None