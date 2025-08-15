from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from config import settings
import enum

# 数据库引擎
engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 用户模型
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联的MCP工具
    mcp_tools = relationship("MCPTool", back_populates="owner", cascade="all, delete-orphan")

# MCP工具状态枚举
class MCPToolStatus(str, enum.Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"

# MCP工具模型
class MCPTool(Base):
    __tablename__ = "mcp_tools"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(200), nullable=False)
    status = Column(String(20), default=MCPToolStatus.STOPPED)
    endpoint_url = Column(String(500))  # WebSocket端点URL
    process_id = Column(Integer, nullable=True)  # 进程ID
    
    # 外键关联用户
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="mcp_tools")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_started_at = Column(DateTime(timezone=True), nullable=True)
    last_stopped_at = Column(DateTime(timezone=True), nullable=True)
    
    # 运行统计
    total_runs = Column(Integer, default=0)
    total_runtime_seconds = Column(Integer, default=0)

# 验证码会话模型
class CaptchaSession(Base):
    __tablename__ = "captcha_sessions"
    
    id = Column(String(36), primary_key=True)  # UUID
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    ip_address = Column(String(45))  # 支持IPv6

# 系统日志模型
class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    module = Column(String(50))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    mcp_tool_id = Column(Integer, ForeignKey("mcp_tools.id"), nullable=True)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 数据库依赖项
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 创建所有表
def create_tables():
    Base.metadata.create_all(bind=engine)