import os
import aiofiles
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db, User, MCPTool, MCPToolStatus, SystemLog
from auth import get_current_user
from schemas import (
    MCPToolCreate, MCPToolUpdate, MCPToolResponse, MCPToolListResponse,
    MessageResponse, FileUploadResponse, UserStatsResponse
)
from config import settings
from mcp_manager import mcp_manager

router = APIRouter()

async def save_uploaded_file(file: UploadFile, user_id: int) -> tuple[str, str]:
    """保存上传的文件"""
    # 验证文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.allowed_file_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_file_extensions)}"
        )
    
    # 验证文件大小
    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )
    
    # 创建用户专用目录
    user_dir = os.path.join(settings.mcp_workspace_dir, f"user_{user_id}")
    os.makedirs(user_dir, exist_ok=True)
    
    # 生成唯一文件名
    import uuid
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(user_dir, unique_filename)
    
    # 保存文件
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    return file_path, unique_filename

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """上传MCP工具文件"""
    file_path, unique_filename = await save_uploaded_file(file, current_user.id)
    
    # 读取文件内容预览
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        preview = content[:500] + "..." if len(content) > 500 else content
    
    return FileUploadResponse(
        filename=unique_filename,
        size=os.path.getsize(file_path),
        content_preview=preview
    )

@router.post("/", response_model=MCPToolResponse)
async def create_mcp_tool(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    endpoint_url: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的MCP工具"""
    # 检查用户工具数量限制
    user_tools_count = db.query(MCPTool).filter(MCPTool.owner_id == current_user.id).count()
    if user_tools_count >= settings.max_mcp_tools_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of tools reached ({settings.max_mcp_tools_per_user})"
        )
    
    # 检查工具名称是否重复
    existing_tool = db.query(MCPTool).filter(
        and_(MCPTool.name == name, MCPTool.owner_id == current_user.id)
    ).first()
    if existing_tool:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool name already exists"
        )
    
    # 保存上传的文件
    file_path, unique_filename = await save_uploaded_file(file, current_user.id)
    
    # 创建MCP工具记录
    mcp_tool = MCPTool(
        name=name,
        description=description,
        file_path=file_path,
        original_filename=file.filename,
        endpoint_url=endpoint_url,
        owner_id=current_user.id
    )
    
    db.add(mcp_tool)
    db.commit()
    db.refresh(mcp_tool)
    
    # 记录系统日志
    log_entry = SystemLog(
        level="INFO",
        message=f"Created MCP tool: {name}",
        module="MCP_Tools",
        user_id=current_user.id,
        mcp_tool_id=mcp_tool.id
    )
    db.add(log_entry)
    db.commit()
    
    return mcp_tool

@router.get("/", response_model=MCPToolListResponse)
async def list_mcp_tools(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的MCP工具列表"""
    offset = (page - 1) * page_size
    
    tools_query = db.query(MCPTool).filter(MCPTool.owner_id == current_user.id)
    total = tools_query.count()
    tools = tools_query.offset(offset).limit(page_size).all()
    
    return MCPToolListResponse(
        tools=tools,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{tool_id}", response_model=MCPToolResponse)
async def get_mcp_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取特定MCP工具详情"""
    tool = db.query(MCPTool).filter(
        and_(MCPTool.id == tool_id, MCPTool.owner_id == current_user.id)
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP tool not found"
        )
    
    return tool

@router.put("/{tool_id}", response_model=MCPToolResponse)
async def update_mcp_tool(
    tool_id: int,
    tool_update: MCPToolUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新MCP工具信息"""
    tool = db.query(MCPTool).filter(
        and_(MCPTool.id == tool_id, MCPTool.owner_id == current_user.id)
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP tool not found"
        )
    
    # 检查工具是否正在运行
    if tool.status == MCPToolStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update running tool. Please stop it first."
        )
    
    # 更新字段
    update_data = tool_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool, field, value)
    
    db.commit()
    db.refresh(tool)
    
    return tool

@router.delete("/{tool_id}", response_model=MessageResponse)
async def delete_mcp_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除MCP工具"""
    tool = db.query(MCPTool).filter(
        and_(MCPTool.id == tool_id, MCPTool.owner_id == current_user.id)
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP tool not found"
        )
    
    # 如果工具正在运行，先停止
    if tool.status in [MCPToolStatus.RUNNING, MCPToolStatus.STARTING]:
        await mcp_manager.stop_mcp_tool(db, tool)
    
    # 删除文件
    if os.path.exists(tool.file_path):
        os.remove(tool.file_path)
    
    # 删除数据库记录
    db.delete(tool)
    db.commit()
    
    return MessageResponse(message="MCP tool deleted successfully")

@router.post("/{tool_id}/start", response_model=MessageResponse)
async def start_mcp_tool(
    tool_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """启动MCP工具"""
    tool = db.query(MCPTool).filter(
        and_(MCPTool.id == tool_id, MCPTool.owner_id == current_user.id)
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP tool not found"
        )
    
    if tool.status == MCPToolStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool is already running"
        )
    
    # 验证文件是否存在
    if not os.path.exists(tool.file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool file not found"
        )
    
    # 后台启动工具
    background_tasks.add_task(mcp_manager.start_mcp_tool, db, tool)
    
    return MessageResponse(message="MCP tool start initiated")

@router.post("/{tool_id}/stop", response_model=MessageResponse)
async def stop_mcp_tool(
    tool_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """停止MCP工具"""
    tool = db.query(MCPTool).filter(
        and_(MCPTool.id == tool_id, MCPTool.owner_id == current_user.id)
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP tool not found"
        )
    
    if tool.status == MCPToolStatus.STOPPED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool is already stopped"
        )
    
    # 后台停止工具
    background_tasks.add_task(mcp_manager.stop_mcp_tool, db, tool)
    
    return MessageResponse(message="MCP tool stop initiated")

@router.get("/{tool_id}/logs")
async def get_tool_logs(
    tool_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取工具日志"""
    tool = db.query(MCPTool).filter(
        and_(MCPTool.id == tool_id, MCPTool.owner_id == current_user.id)
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP tool not found"
        )
    
    logs = db.query(SystemLog).filter(
        SystemLog.mcp_tool_id == tool_id
    ).order_by(SystemLog.created_at.desc()).limit(limit).all()
    
    return {"logs": logs}

@router.get("/stats/user", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户统计信息"""
    user_tools = db.query(MCPTool).filter(MCPTool.owner_id == current_user.id).all()
    
    total_tools = len(user_tools)
    running_tools = sum(1 for tool in user_tools if tool.status == MCPToolStatus.RUNNING)
    total_runs = sum(tool.total_runs for tool in user_tools)
    total_runtime_seconds = sum(tool.total_runtime_seconds for tool in user_tools)
    
    return UserStatsResponse(
        total_tools=total_tools,
        running_tools=running_tools,
        total_runs=total_runs,
        total_runtime_hours=total_runtime_seconds / 3600
    )