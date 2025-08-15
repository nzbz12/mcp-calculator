from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db, User, MCPTool, SystemLog
from auth import get_current_admin_user
from schemas import AdminStatsResponse, SystemLogResponse, UserResponse

router = APIRouter()

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取管理员统计信息"""
    total_users = db.query(User).count()
    total_tools = db.query(MCPTool).count()
    running_tools = db.query(MCPTool).filter(MCPTool.status == "running").count()
    total_system_logs = db.query(SystemLog).count()
    
    return AdminStatsResponse(
        total_users=total_users,
        total_tools=total_tools,
        running_tools=running_tools,
        total_system_logs=total_system_logs
    )

@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    page: int = 1,
    page_size: int = 50,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取所有用户列表"""
    offset = (page - 1) * page_size
    users = db.query(User).offset(offset).limit(page_size).all()
    return users

@router.get("/logs", response_model=List[SystemLogResponse])
async def get_system_logs(
    page: int = 1,
    page_size: int = 100,
    level: str = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取系统日志"""
    offset = (page - 1) * page_size
    query = db.query(SystemLog)
    
    if level:
        query = query.filter(SystemLog.level == level.upper())
    
    logs = query.order_by(SystemLog.created_at.desc()).offset(offset).limit(page_size).all()
    return logs

@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """切换用户激活状态"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_admin and user.id != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate other admin users"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    return {"message": f"User {'activated' if user.is_active else 'deactivated'} successfully"}