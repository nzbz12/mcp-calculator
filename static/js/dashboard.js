// 仪表板管理

class Dashboard {
    constructor() {
        this.tools = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalPages = 1;
        this.websocket = null;
        
        this.init();
    }

    async init() {
        // 检查登录状态
        if (!auth.isLoggedIn()) {
            window.location.href = '/login';
            return;
        }

        // 设置文件上传
        this.setupFileUpload();
        
        // 加载数据
        await this.loadStats();
        await this.loadTools();
        
        // 建立WebSocket连接
        this.connectWebSocket();
        
        // 设置定时刷新
        setInterval(() => {
            this.loadStats();
        }, 30000); // 30秒刷新一次统计
    }

    // 设置文件上传
    setupFileUpload() {
        const fileUploadArea = document.getElementById('fileUploadArea');
        const fileInput = document.getElementById('toolFile');
        
        // 点击上传区域
        fileUploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // 文件选择
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });
        
        // 拖拽上传
        setupFileDrop(fileUploadArea, (files) => {
            if (files.length > 0) {
                fileInput.files = files;
                this.handleFileSelect(files[0]);
            }
        });
    }

    // 处理文件选择
    async handleFileSelect(file) {
        if (!file) return;
        
        const preview = document.getElementById('filePreview');
        const content = document.getElementById('fileContent');
        
        try {
            const text = await file.text();
            content.textContent = text.substring(0, 2000) + (text.length > 2000 ? '\n...(文件太长，仅显示前2000字符)' : '');
            preview.style.display = 'block';
        } catch (error) {
            showNotification('无法预览文件内容', 'warning');
        }
    }

    // 建立WebSocket连接
    connectWebSocket() {
        const token = auth.getToken();
        if (!token) return;
        
        const wsUrl = `ws://localhost:8000/ws/status?token=${token}`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                // 5秒后重连
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
        }
    }

    // 处理WebSocket消息
    handleWebSocketMessage(message) {
        if (message.type === 'status_update') {
            this.updateToolStatus(message.data.tool_id, message.data.status);
            showNotification(`工具 ${message.data.tool_name} 状态更新: ${message.data.status}`, 'info');
        }
    }

    // 更新工具状态
    updateToolStatus(toolId, status) {
        const tool = this.tools.find(t => t.id === toolId);
        if (tool) {
            tool.status = status;
            this.renderToolsTable();
            this.loadStats(); // 刷新统计
        }
    }

    // 加载统计数据
    async loadStats() {
        try {
            const response = await axios.get('/api/tools/stats/user');
            const stats = response.data;
            
            document.getElementById('total-tools').textContent = stats.total_tools;
            document.getElementById('running-tools').textContent = stats.running_tools;
            document.getElementById('total-runs').textContent = stats.total_runs;
            document.getElementById('total-runtime').textContent = stats.total_runtime_hours.toFixed(1) + 'h';
            
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    // 加载工具列表
    async loadTools(page = 1) {
        try {
            showLoading();
            const response = await axios.get(`/api/tools/?page=${page}&page_size=${this.pageSize}`);
            
            this.tools = response.data.tools;
            this.currentPage = page;
            this.totalPages = Math.ceil(response.data.total / this.pageSize);
            
            this.renderToolsTable();
            this.renderPagination();
            
        } catch (error) {
            showNotification('加载工具列表失败', 'error');
            console.error('Failed to load tools:', error);
        } finally {
            hideLoading();
        }
    }

    // 渲染工具表格
    renderToolsTable() {
        const tbody = document.getElementById('tools-table-body');
        
        if (this.tools.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-4">
                        <i class="fas fa-inbox fa-3x mb-3"></i>
                        <br>还没有创建任何工具
                        <br><button class="btn btn-primary btn-sm mt-2" onclick="showCreateToolModal()">
                            <i class="fas fa-plus"></i> 创建第一个工具
                        </button>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = this.tools.map(tool => `
            <tr class="tool-row tool-${tool.status}">
                <td>
                    <div class="fw-bold">${tool.name}</div>
                    ${tool.description ? `<small class="text-muted">${tool.description}</small>` : ''}
                </td>
                <td>${getStatusBadge(tool.status)}</td>
                <td>
                    <small class="text-muted">${tool.original_filename}</small>
                </td>
                <td>
                    <small>${formatDateTime(tool.created_at)}</small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        ${this.getToolActionButtons(tool)}
                    </div>
                </td>
            </tr>
        `).join('');
    }

    // 获取工具操作按钮
    getToolActionButtons(tool) {
        const buttons = [];
        
        if (tool.status === 'stopped') {
            buttons.push(`<button class="btn btn-success" onclick="dashboard.startTool(${tool.id})" title="启动">
                <i class="fas fa-play"></i>
            </button>`);
        } else if (tool.status === 'running') {
            buttons.push(`<button class="btn btn-warning" onclick="dashboard.stopTool(${tool.id})" title="停止">
                <i class="fas fa-stop"></i>
            </button>`);
        }
        
        buttons.push(`<button class="btn btn-info" onclick="dashboard.showToolDetail(${tool.id})" title="详情">
            <i class="fas fa-info"></i>
        </button>`);
        
        buttons.push(`<button class="btn btn-danger" onclick="dashboard.deleteTool(${tool.id})" title="删除">
            <i class="fas fa-trash"></i>
        </button>`);
        
        return buttons.join('');
    }

    // 渲染分页
    renderPagination() {
        const container = document.getElementById('pagination-container');
        const pagination = document.getElementById('pagination');
        
        if (this.totalPages <= 1) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        
        let html = '';
        
        // 上一页
        html += `<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="dashboard.loadTools(${this.currentPage - 1})">上一页</a>
        </li>`;
        
        // 页码
        for (let i = 1; i <= this.totalPages; i++) {
            if (i === this.currentPage || i === 1 || i === this.totalPages || 
                (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                html += `<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="dashboard.loadTools(${i})">${i}</a>
                </li>`;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                html += `<li class="page-item disabled">
                    <span class="page-link">...</span>
                </li>`;
            }
        }
        
        // 下一页
        html += `<li class="page-item ${this.currentPage === this.totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="dashboard.loadTools(${this.currentPage + 1})">下一页</a>
        </li>`;
        
        pagination.innerHTML = html;
    }

    // 启动工具
    async startTool(toolId) {
        try {
            showLoading();
            await axios.post(`/api/tools/${toolId}/start`);
            showNotification('工具启动指令已发送', 'success');
            
            // 更新本地状态
            const tool = this.tools.find(t => t.id === toolId);
            if (tool) {
                tool.status = 'starting';
                this.renderToolsTable();
            }
            
        } catch (error) {
            if (error.response && error.response.data && error.response.data.detail) {
                showNotification(error.response.data.detail, 'error');
            } else {
                showNotification('启动工具失败', 'error');
            }
        } finally {
            hideLoading();
        }
    }

    // 停止工具
    async stopTool(toolId) {
        try {
            showLoading();
            await axios.post(`/api/tools/${toolId}/stop`);
            showNotification('工具停止指令已发送', 'success');
            
            // 更新本地状态
            const tool = this.tools.find(t => t.id === toolId);
            if (tool) {
                tool.status = 'stopping';
                this.renderToolsTable();
            }
            
        } catch (error) {
            if (error.response && error.response.data && error.response.data.detail) {
                showNotification(error.response.data.detail, 'error');
            } else {
                showNotification('停止工具失败', 'error');
            }
        } finally {
            hideLoading();
        }
    }

    // 删除工具
    async deleteTool(toolId) {
        const tool = this.tools.find(t => t.id === toolId);
        if (!tool) return;
        
        confirmAction(`确定要删除工具 "${tool.name}" 吗？此操作不可撤销。`, async () => {
            try {
                showLoading();
                await axios.delete(`/api/tools/${toolId}`);
                showNotification('工具删除成功', 'success');
                
                // 重新加载列表
                await this.loadTools(this.currentPage);
                await this.loadStats();
                
            } catch (error) {
                if (error.response && error.response.data && error.response.data.detail) {
                    showNotification(error.response.data.detail, 'error');
                } else {
                    showNotification('删除工具失败', 'error');
                }
            } finally {
                hideLoading();
            }
        });
    }

    // 显示工具详情
    async showToolDetail(toolId) {
        try {
            showLoading();
            const response = await axios.get(`/api/tools/${toolId}`);
            const tool = response.data;
            
            document.getElementById('toolDetailTitle').innerHTML = `
                <i class="fas fa-info-circle"></i> ${tool.name}
            `;
            
            document.getElementById('toolDetailContent').innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>基本信息</h6>
                        <table class="table table-sm">
                            <tr><td>名称:</td><td>${tool.name}</td></tr>
                            <tr><td>状态:</td><td>${getStatusBadge(tool.status)}</td></tr>
                            <tr><td>文件:</td><td>${tool.original_filename}</td></tr>
                            <tr><td>创建时间:</td><td>${formatDateTime(tool.created_at)}</td></tr>
                            ${tool.description ? `<tr><td>描述:</td><td>${tool.description}</td></tr>` : ''}
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h6>运行统计</h6>
                        <table class="table table-sm">
                            <tr><td>总运行次数:</td><td>${tool.total_runs}</td></tr>
                            <tr><td>总运行时间:</td><td>${formatRuntime(tool.total_runtime_seconds)}</td></tr>
                            ${tool.last_started_at ? `<tr><td>最后启动:</td><td>${formatDateTime(tool.last_started_at)}</td></tr>` : ''}
                            ${tool.last_stopped_at ? `<tr><td>最后停止:</td><td>${formatDateTime(tool.last_stopped_at)}</td></tr>` : ''}
                            ${tool.process_id ? `<tr><td>进程ID:</td><td>${tool.process_id}</td></tr>` : ''}
                        </table>
                    </div>
                </div>
                <div class="mt-3">
                    <h6>WebSocket端点</h6>
                    <div class="input-group">
                        <input type="text" class="form-control" value="${tool.endpoint_url}" readonly>
                        <button class="btn btn-outline-secondary" onclick="copyToClipboard('${tool.endpoint_url}')">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
            `;
            
            ModalManager.show('toolDetailModal');
            
        } catch (error) {
            showNotification('加载工具详情失败', 'error');
        } finally {
            hideLoading();
        }
    }
}

// 显示创建工具模态框
function showCreateToolModal() {
    // 重置表单
    document.getElementById('createToolForm').reset();
    document.getElementById('filePreview').style.display = 'none';
    
    ModalManager.show('createToolModal');
}

// 创建工具
async function createTool() {
    const form = document.getElementById('createToolForm');
    const formData = new FormData(form);
    
    // 验证必填字段
    if (!formData.get('name') || !formData.get('endpoint_url') || !formData.get('file')) {
        showNotification('请填写所有必填字段', 'error');
        return;
    }
    
    try {
        showLoading();
        const response = await axios.post('/api/tools/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        
        showNotification('工具创建成功', 'success');
        
        // 隐藏模态框
        ModalManager.hide('createToolModal');
        
        // 重新加载列表
        await dashboard.loadTools();
        await dashboard.loadStats();
        
    } catch (error) {
        if (error.response && error.response.data && error.response.data.detail) {
            showNotification(error.response.data.detail, 'error');
        } else {
            showNotification('创建工具失败', 'error');
        }
    } finally {
        hideLoading();
    }
}

// 启动所有工具
async function startAllTools() {
    const stoppedTools = dashboard.tools.filter(t => t.status === 'stopped');
    
    if (stoppedTools.length === 0) {
        showNotification('没有可启动的工具', 'info');
        return;
    }
    
    confirmAction(`确定要启动 ${stoppedTools.length} 个工具吗？`, async () => {
        for (const tool of stoppedTools) {
            try {
                await dashboard.startTool(tool.id);
                await new Promise(resolve => setTimeout(resolve, 1000)); // 间隔1秒
            } catch (error) {
                console.error(`Failed to start tool ${tool.id}:`, error);
            }
        }
    });
}

// 停止所有工具
async function stopAllTools() {
    const runningTools = dashboard.tools.filter(t => t.status === 'running');
    
    if (runningTools.length === 0) {
        showNotification('没有正在运行的工具', 'info');
        return;
    }
    
    confirmAction(`确定要停止 ${runningTools.length} 个工具吗？`, async () => {
        for (const tool of runningTools) {
            try {
                await dashboard.stopTool(tool.id);
                await new Promise(resolve => setTimeout(resolve, 500)); // 间隔0.5秒
            } catch (error) {
                console.error(`Failed to stop tool ${tool.id}:`, error);
            }
        }
    });
}

// 刷新工具列表
async function refreshToolsList() {
    await dashboard.loadTools(dashboard.currentPage);
    await dashboard.loadStats();
    showNotification('列表已刷新', 'success');
}

// 创建仪表板实例
const dashboard = new Dashboard();

// 导出到全局
window.dashboard = dashboard;