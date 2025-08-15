# MCP Cloud Studio | MCP工具云管理平台

一个专业的AI工具集成与管理平台，让您轻松部署、管理和监控自定义MCP工具。

![MCP Cloud Studio](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

## ✨ 功能特性

### 🔐 用户认证系统
- JWT身份验证
- 图形验证码保护
- 安全的密码哈希存储
- 用户权限管理

### 📁 文件管理
- 支持拖拽上传
- 多种文件格式支持 (.py, .txt, .json, .yaml, .yml)
- 文件大小限制和类型验证
- 安全的文件存储机制

### ⚡ MCP工具管理
- 一键启动/停止工具
- 实时状态监控
- WebSocket状态更新
- 进程自动管理
- 异常处理和日志记录

### 📊 监控与统计
- 实时运行状态监控
- 详细的运行统计
- 系统日志管理
- 性能指标收集

### 🎨 现代化UI
- 响应式设计
- Bootstrap 5界面
- 直观的用户体验
- 实时通知系统

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip包管理器
- 现代浏览器

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd mcp-cloud-studio
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境**
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

4. **启动应用**
```bash
python run.py
```

5. **访问应用**
```
打开浏览器访问: http://localhost:8000
```

## 📋 使用说明

### 1. 注册账户
- 访问注册页面创建账户
- 输入用户名、邮箱和密码
- 完成图形验证码验证

### 2. 登录系统
- 使用注册的用户名和密码登录
- 验证图形验证码
- 成功登录后进入仪表板

### 3. 创建MCP工具
- 点击"新建工具"按钮
- 填写工具名称和描述
- 配置WebSocket端点URL
- 上传Python工具文件
- 点击创建完成

### 4. 管理工具
- 在仪表板查看所有工具
- 一键启动/停止工具
- 查看工具运行状态
- 监控运行统计信息

## 🏗️ 项目结构

```
mcp-cloud-studio/
├── main.py                 # FastAPI主应用
├── run.py                  # 启动脚本
├── config.py               # 配置管理
├── database.py             # 数据库模型
├── auth.py                 # 认证模块
├── mcp_manager.py          # MCP工具管理
├── schemas.py              # Pydantic模型
├── requirements.txt        # Python依赖
├── .env.example           # 环境配置示例
├── routes/                # API路由
│   ├── auth.py            # 认证相关API
│   ├── mcp_tools.py       # 工具管理API
│   ├── admin.py           # 管理员API
│   └── websocket.py       # WebSocket路由
├── templates/             # Jinja2模板
│   ├── base.html          # 基础模板
│   ├── index.html         # 主页
│   ├── login.html         # 登录页
│   ├── register.html      # 注册页
│   └── dashboard.html     # 仪表板
├── static/                # 静态文件
│   ├── css/
│   │   └── main.css       # 主样式文件
│   └── js/
│       ├── auth.js        # 认证管理
│       ├── utils.js       # 工具函数
│       └── dashboard.js   # 仪表板功能
└── calculator.py          # 示例MCP工具
```

## 🔧 配置说明

### 环境变量

主要配置项说明：

- `SECRET_KEY`: JWT签名密钥（生产环境必须更改）
- `DATABASE_URL`: 数据库连接字符串
- `MAX_MCP_TOOLS_PER_USER`: 每用户最大工具数量
- `MAX_FILE_SIZE_MB`: 文件上传大小限制
- `LOG_LEVEL`: 日志级别 (DEBUG, INFO, WARNING, ERROR)

### WebSocket端点配置

默认WebSocket端点已预配置为小智API：
```
wss://api.xiaozhi.me/mcp/?token=<your-token>
```

您可以在创建工具时修改为自己的端点。

## 🛠️ 开发指南

### 添加新的API路由

1. 在 `routes/` 目录下创建新的路由文件
2. 在 `main.py` 中注册路由
3. 添加相应的数据模型到 `schemas.py`

### 自定义MCP工具

参考 `calculator.py` 创建自己的MCP工具：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("YourToolName")

@mcp.tool()
def your_function(parameter: str) -> dict:
    """工具描述"""
    # 实现逻辑
    return {"success": True, "result": "结果"}

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

## 🔒 安全考虑

### 生产环境部署

1. **更改默认密钥**
```bash
# 生成强密钥
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
```

2. **使用HTTPS**
```bash
# 配置反向代理或SSL证书
```

3. **限制文件上传**
```bash
# 配置文件类型和大小限制
MAX_FILE_SIZE_MB=5
ALLOWED_FILE_EXTENSIONS=[".py"]
```

4. **配置防火墙**
```bash
# 仅开放必要端口
```

## 📊 监控与日志

### 系统日志

应用会自动记录以下日志：
- 用户认证日志
- MCP工具运行日志
- 系统错误日志
- API访问日志

### 性能监控

可以通过以下方式监控系统性能：
- 查看 `/health` 端点
- 检查数据库连接状态
- 监控WebSocket连接数

## 🐛 故障排除

### 常见问题

1. **启动失败**
```bash
# 检查端口是否被占用
netstat -tulpn | grep 8000

# 检查Python依赖
pip list
```

2. **数据库错误**
```bash
# 删除数据库文件重新初始化
rm mcp_studio.db
python run.py
```

3. **WebSocket连接失败**
```bash
# 检查网络连接和端点配置
```

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详情请查看 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Web框架
- [Bootstrap](https://getbootstrap.com/) - 响应式UI框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL工具包
- [MCP](https://github.com/modelcontextprotocol/python-sdk) - 模型上下文协议

## 📞 联系我们

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 参与讨论

---

**MCP Cloud Studio** - 让AI工具管理变得简单高效！ 🚀