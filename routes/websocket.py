import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Set

from database import get_db, User
from auth import verify_token
from schemas import WSMessage

router = APIRouter()

# 存储WebSocket连接
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}  # user_id -> set of websockets
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            dead_connections = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    dead_connections.add(websocket)
            
            # 清理断开的连接
            for websocket in dead_connections:
                self.active_connections[user_id].discard(websocket)
    
    async def broadcast_to_all(self, message: dict):
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

manager = ConnectionManager()

@router.websocket("/status")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket端点用于实时状态更新"""
    # 验证用户token
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    username = payload.get("sub")
    if not username:
        await websocket.close(code=4001, reason="Invalid token payload")
        return
    
    # 获取用户信息
    from database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            await websocket.close(code=4003, reason="User not found or inactive")
            return
        
        await manager.connect(websocket, user.id)
        
        try:
            while True:
                # 保持连接活跃，可以接收客户端的ping消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, user.id)
    finally:
        db.close()

# 工具状态更新回调函数
async def tool_status_callback(tool_id: int, status: str):
    """MCP工具状态变化时的回调函数"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        from database import MCPTool
        tool = db.query(MCPTool).filter(MCPTool.id == tool_id).first()
        if tool:
            message = WSMessage(
                type="status_update",
                tool_id=tool_id,
                data={
                    "tool_id": tool_id,
                    "tool_name": tool.name,
                    "status": status,
                    "timestamp": tool.last_started_at.isoformat() if tool.last_started_at else None
                }
            )
            await manager.send_to_user(tool.owner_id, message.dict())
    finally:
        db.close()

# 获取连接管理器实例（供其他模块使用）
def get_connection_manager():
    return manager