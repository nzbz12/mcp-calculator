#!/usr/bin/env python3
"""
MCP Cloud Studio - 启动脚本
运行这个脚本来启动应用
"""

import uvicorn
import logging
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings

def main():
    """主启动函数"""
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('mcp_studio.log', encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger('MCP_Studio')
    
    logger.info("=" * 60)
    logger.info("🚀 启动 MCP Cloud Studio")
    logger.info(f"版本: {settings.app_version}")
    logger.info(f"主机: {settings.host}:{settings.port}")
    logger.info(f"调试模式: {settings.debug}")
    logger.info("=" * 60)
    
    try:
        # 启动应用
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True,
            workers=1 if settings.debug else 4
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭应用...")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()