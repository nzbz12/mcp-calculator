import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from config import settings
from database import create_tables
from routes import auth, mcp_tools, admin, websocket
from mcp_manager import mcp_manager

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MCP_Studio')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting MCP Cloud Studio...")
    
    # 创建数据库表
    create_tables()
    logger.info("Database tables created/verified")
    
    # 创建静态文件目录
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    yield
    
    # 关闭时
    logger.info("Shutting down MCP Cloud Studio...")
    # 这里可以添加清理逻辑

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A powerful interface for extending AI capabilities through MCP tools",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板引擎
templates = Jinja2Templates(directory="templates")

# 包含路由
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(mcp_tools.router, prefix="/api/tools", tags=["MCP Tools"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

# 根路径 - 返回前端应用
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

# 登录页面
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

# 注册页面
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页面"""
    return templates.TemplateResponse("register.html", {"request": request})

# 仪表板页面
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """仪表板页面"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "running_tools": len(mcp_manager.get_running_tools())
    }

# 全局异常处理器
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """404错误处理"""
    if request.url.path.startswith("/api/"):
        return {"detail": "API endpoint not found"}
    # 对于非API路径，返回前端应用（SPA路由）
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    # 开发模式运行
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )