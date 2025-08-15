#!/usr/bin/env python3
"""
MCP Cloud Studio - 快速启动脚本
用于演示和快速体验平台功能
"""

import os
import sys
import subprocess
import secrets
from pathlib import Path

def create_env_file():
    """创建环境配置文件"""
    env_content = f"""# MCP Cloud Studio 环境配置
# 自动生成的配置文件

# 应用基础配置
APP_NAME=MCP Cloud Studio
APP_VERSION=1.0.0
DEBUG=true

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=sqlite:///./mcp_studio.db

# JWT安全配置
SECRET_KEY={secrets.token_urlsafe(32)}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 验证码配置
CAPTCHA_LENGTH=4
CAPTCHA_WIDTH=120
CAPTCHA_HEIGHT=40

# MCP配置
MCP_WORKSPACE_DIR=./mcp_workspace
MAX_MCP_TOOLS_PER_USER=10
MAX_FILE_SIZE_MB=10

# WebSocket配置
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300

# 监控配置
ENABLE_METRICS=true
LOG_LEVEL=INFO

# 文件上传配置
UPLOAD_DIR=./uploads
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 环境配置文件 .env 已创建")

def install_dependencies():
    """安装依赖包"""
    print("📦 正在安装依赖包...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], check=True, capture_output=True, text=True)
        print("✅ 依赖包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖包安装失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def create_admin_user():
    """创建管理员用户的示例脚本"""
    admin_script = """
# 创建管理员用户的示例代码
from database import SessionLocal, User, create_tables
from auth import get_password_hash

def create_admin():
    create_tables()
    db = SessionLocal()
    
    # 检查是否已存在管理员
    existing_admin = db.query(User).filter(User.is_admin == True).first()
    if existing_admin:
        print("管理员用户已存在")
        return
    
    # 创建管理员用户
    admin_user = User(
        username="admin",
        email="admin@mcpstudio.com",
        hashed_password=get_password_hash("admin123"),
        is_admin=True
    )
    
    db.add(admin_user)
    db.commit()
    print("管理员用户创建成功:")
    print("用户名: admin")
    print("密码: admin123")
    print("请在生产环境中更改密码！")
    
    db.close()

if __name__ == "__main__":
    create_admin()
"""
    
    with open('create_admin.py', 'w', encoding='utf-8') as f:
        f.write(admin_script)
    
    print("✅ 管理员创建脚本已生成: create_admin.py")

def show_startup_info():
    """显示启动信息"""
    print("\n" + "="*60)
    print("🎉 MCP Cloud Studio 快速启动配置完成！")
    print("="*60)
    print("\n📋 启动步骤:")
    print("1. 启动应用:")
    print("   python run.py")
    print("\n2. 访问应用:")
    print("   http://localhost:8000")
    print("\n3. 创建管理员账户（可选）:")
    print("   python create_admin.py")
    print("\n🔧 功能特性:")
    print("- 用户注册/登录（带图形验证码）")
    print("- MCP工具文件上传管理")
    print("- 一键启动/停止工具")
    print("- 实时状态监控")
    print("- WebSocket实时更新")
    print("\n📖 使用说明:")
    print("1. 访问主页注册账户")
    print("2. 登录后进入仪表板")
    print("3. 上传MCP工具文件（如calculator.py）")
    print("4. 配置WebSocket端点URL")
    print("5. 启动工具开始使用")
    print("\n🔗 默认WebSocket端点:")
    print("wss://api.xiaozhi.me/mcp/?token=<your-token>")
    print("\n⚠️  注意事项:")
    print("- 生产环境请修改SECRET_KEY")
    print("- 确保WebSocket端点可访问")
    print("- 定期备份数据库文件")
    print("\n" + "="*60)

def main():
    """主函数"""
    print("🚀 MCP Cloud Studio 快速启动配置")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 创建环境配置
    if not os.path.exists('.env'):
        create_env_file()
    else:
        print("ℹ️  环境配置文件已存在，跳过创建")
    
    # 创建管理员脚本
    create_admin_user()
    
    # 安装依赖
    if not install_dependencies():
        print("❌ 依赖安装失败，请手动运行: pip install -r requirements.txt")
        return
    
    # 显示启动信息
    show_startup_info()
    
    # 询问是否立即启动
    choice = input("\n是否立即启动应用？(y/N): ").strip().lower()
    if choice in ['y', 'yes']:
        print("\n🚀 正在启动应用...")
        try:
            os.system("python run.py")
        except KeyboardInterrupt:
            print("\n\n👋 应用已停止")

if __name__ == "__main__":
    main()