import asyncio
import websockets
import subprocess
import logging
import os
import signal
import sys
import psutil
from datetime import datetime
from typing import Dict, Optional, Callable
from sqlalchemy.orm import Session

from config import settings
from database import MCPTool, MCPToolStatus, SystemLog

logger = logging.getLogger('MCP_Manager')

class MCPProcessManager:
    """MCP工具进程管理器"""
    
    def __init__(self):
        self.processes: Dict[int, subprocess.Popen] = {}
        self.websocket_connections: Dict[int, asyncio.Task] = {}
        
    async def start_mcp_tool(self, db: Session, tool: MCPTool, 
                           status_callback: Optional[Callable] = None) -> bool:
        """启动MCP工具"""
        try:
            # 更新状态为启动中
            tool.status = MCPToolStatus.STARTING
            tool.last_started_at = datetime.utcnow()
            tool.total_runs += 1
            db.commit()
            
            if status_callback:
                await status_callback(tool.id, MCPToolStatus.STARTING)
            
            # 启动WebSocket连接任务
            task = asyncio.create_task(
                self._run_mcp_connection(db, tool, status_callback)
            )
            self.websocket_connections[tool.id] = task
            
            logger.info(f"Started MCP tool {tool.name} (ID: {tool.id})")
            return True
            
        except Exception as e:
            # 更新状态为错误
            tool.status = MCPToolStatus.ERROR
            db.commit()
            
            if status_callback:
                await status_callback(tool.id, MCPToolStatus.ERROR)
            
            logger.error(f"Failed to start MCP tool {tool.name}: {e}")
            
            # 记录系统日志
            log_entry = SystemLog(
                level="ERROR",
                message=f"Failed to start MCP tool {tool.name}: {str(e)}",
                module="MCP_Manager",
                user_id=tool.owner_id,
                mcp_tool_id=tool.id
            )
            db.add(log_entry)
            db.commit()
            
            return False
    
    async def stop_mcp_tool(self, db: Session, tool: MCPTool,
                          status_callback: Optional[Callable] = None) -> bool:
        """停止MCP工具"""
        try:
            # 更新状态为停止中
            tool.status = MCPToolStatus.STOPPING
            db.commit()
            
            if status_callback:
                await status_callback(tool.id, MCPToolStatus.STOPPING)
            
            # 取消WebSocket连接任务
            if tool.id in self.websocket_connections:
                task = self.websocket_connections[tool.id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.websocket_connections[tool.id]
            
            # 终止进程
            if tool.process_id and tool.process_id in self.processes:
                process = self.processes[tool.process_id]
                try:
                    process.terminate()
                    await asyncio.sleep(2)  # 给进程2秒时间优雅关闭
                    
                    if process.poll() is None:  # 进程仍在运行
                        process.kill()
                        
                    process.wait()
                except:
                    pass
                
                del self.processes[tool.process_id]
            
            # 更新状态
            tool.status = MCPToolStatus.STOPPED
            tool.last_stopped_at = datetime.utcnow()
            tool.process_id = None
            
            # 计算运行时间
            if tool.last_started_at:
                runtime = (datetime.utcnow() - tool.last_started_at).total_seconds()
                tool.total_runtime_seconds += int(runtime)
            
            db.commit()
            
            if status_callback:
                await status_callback(tool.id, MCPToolStatus.STOPPED)
            
            logger.info(f"Stopped MCP tool {tool.name} (ID: {tool.id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop MCP tool {tool.name}: {e}")
            return False
    
    async def _run_mcp_connection(self, db: Session, tool: MCPTool,
                                status_callback: Optional[Callable] = None):
        """运行MCP工具的WebSocket连接"""
        reconnect_attempt = 0
        max_attempts = 5
        backoff = 1
        
        while reconnect_attempt < max_attempts:
            try:
                if not tool.endpoint_url:
                    raise ValueError("No endpoint URL configured")
                
                await self._connect_to_server(db, tool, status_callback)
                break  # 连接成功，退出重试循环
                
            except Exception as e:
                reconnect_attempt += 1
                logger.warning(f"Connection failed for {tool.name} (attempt {reconnect_attempt}): {e}")
                
                if reconnect_attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)  # 最大60秒
                else:
                    # 达到最大重试次数，标记为错误状态
                    tool.status = MCPToolStatus.ERROR
                    db.commit()
                    
                    if status_callback:
                        await status_callback(tool.id, MCPToolStatus.ERROR)
                    
                    logger.error(f"Max retry attempts reached for {tool.name}")
    
    async def _connect_to_server(self, db: Session, tool: MCPTool,
                               status_callback: Optional[Callable] = None):
        """连接到WebSocket服务器并建立双向通信"""
        try:
            logger.info(f"Connecting to WebSocket server for {tool.name}...")
            
            async with websockets.connect(tool.endpoint_url) as websocket:
                logger.info(f"Successfully connected WebSocket for {tool.name}")
                
                # 启动MCP工具进程
                process = subprocess.Popen(
                    [sys.executable, tool.file_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    text=True,
                    cwd=os.path.dirname(tool.file_path)
                )
                
                # 保存进程信息
                self.processes[process.pid] = process
                tool.process_id = process.pid
                tool.status = MCPToolStatus.RUNNING
                db.commit()
                
                if status_callback:
                    await status_callback(tool.id, MCPToolStatus.RUNNING)
                
                logger.info(f"Started process for {tool.name} (PID: {process.pid})")
                
                # 创建通信任务
                await asyncio.gather(
                    self._pipe_websocket_to_process(websocket, process, tool.name),
                    self._pipe_process_to_websocket(process, websocket, tool.name),
                    self._pipe_process_stderr_to_log(process, tool.name, db, tool.id)
                )
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket connection closed for {tool.name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Connection error for {tool.name}: {e}")
            raise
        finally:
            # 清理进程
            if 'process' in locals():
                try:
                    if process.poll() is None:
                        process.terminate()
                        await asyncio.sleep(2)
                        if process.poll() is None:
                            process.kill()
                    
                    if process.pid in self.processes:
                        del self.processes[process.pid]
                        
                except:
                    pass
    
    async def _pipe_websocket_to_process(self, websocket, process, tool_name: str):
        """将WebSocket消息转发到进程"""
        try:
            while True:
                message = await websocket.recv()
                logger.debug(f"[{tool_name}] << {message[:120]}...")
                
                if isinstance(message, bytes):
                    message = message.decode('utf-8')
                    
                process.stdin.write(message + '\n')
                process.stdin.flush()
                
        except Exception as e:
            logger.error(f"Error in WebSocket to process pipe for {tool_name}: {e}")
            raise
        finally:
            if not process.stdin.closed:
                process.stdin.close()
    
    async def _pipe_process_to_websocket(self, process, websocket, tool_name: str):
        """将进程输出转发到WebSocket"""
        try:
            while True:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, process.stdout.readline
                )
                
                if not data:
                    logger.info(f"[{tool_name}] Process ended output")
                    break
                
                logger.debug(f"[{tool_name}] >> {data[:120]}...")
                await websocket.send(data)
                
        except Exception as e:
            logger.error(f"Error in process to WebSocket pipe for {tool_name}: {e}")
            raise
    
    async def _pipe_process_stderr_to_log(self, process, tool_name: str, 
                                        db: Session, tool_id: int):
        """将进程错误输出记录到日志"""
        try:
            while True:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, process.stderr.readline
                )
                
                if not data:
                    logger.info(f"[{tool_name}] Process ended stderr output")
                    break
                
                # 记录到系统日志
                if data.strip():
                    log_entry = SystemLog(
                        level="WARNING",
                        message=f"[{tool_name}] {data.strip()}",
                        module="MCP_Tool",
                        mcp_tool_id=tool_id
                    )
                    db.add(log_entry)
                    db.commit()
                
                logger.warning(f"[{tool_name}] STDERR: {data.strip()}")
                
        except Exception as e:
            logger.error(f"Error in process stderr pipe for {tool_name}: {e}")
    
    def get_tool_status(self, tool_id: int) -> Optional[MCPToolStatus]:
        """获取工具状态"""
        if tool_id in self.websocket_connections:
            task = self.websocket_connections[tool_id]
            if task.done():
                return MCPToolStatus.ERROR
            else:
                return MCPToolStatus.RUNNING
        return MCPToolStatus.STOPPED
    
    def get_running_tools(self) -> list[int]:
        """获取正在运行的工具列表"""
        return list(self.websocket_connections.keys())
    
    async def shutdown_all(self, db: Session):
        """关闭所有运行中的工具"""
        running_tools = list(self.websocket_connections.keys())
        
        for tool_id in running_tools:
            tool = db.query(MCPTool).filter(MCPTool.id == tool_id).first()
            if tool:
                await self.stop_mcp_tool(db, tool)
        
        logger.info("All MCP tools have been shutdown")

# 全局进程管理器实例
mcp_manager = MCPProcessManager()