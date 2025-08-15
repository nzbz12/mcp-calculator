// 认证管理模块

class AuthManager {
    constructor() {
        this.token = localStorage.getItem('access_token');
        this.user = null;
        this.setupAxiosInterceptors();
        this.loadUserInfo();
    }

    // 设置Axios拦截器
    setupAxiosInterceptors() {
        // 请求拦截器 - 添加Authorization头
        axios.interceptors.request.use(
            (config) => {
                if (this.token) {
                    config.headers.Authorization = `Bearer ${this.token}`;
                }
                return config;
            },
            (error) => {
                return Promise.reject(error);
            }
        );

        // 响应拦截器 - 处理401错误
        axios.interceptors.response.use(
            (response) => {
                return response;
            },
            (error) => {
                if (error.response && error.response.status === 401) {
                    this.logout();
                    showNotification('登录已过期，请重新登录', 'warning');
                    window.location.href = '/login';
                }
                return Promise.reject(error);
            }
        );
    }

    // 加载用户信息
    loadUserInfo() {
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            try {
                this.user = JSON.parse(userInfo);
                this.updateNavbar();
            } catch (e) {
                console.error('Failed to parse user info:', e);
                this.logout();
            }
        }
    }

    // 检查是否已登录
    isLoggedIn() {
        return !!this.token && !!this.user;
    }

    // 获取当前用户
    getCurrentUser() {
        return this.user;
    }

    // 获取token
    getToken() {
        return this.token;
    }

    // 设置token和用户信息
    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('access_token', token);
        localStorage.setItem('user_info', JSON.stringify(user));
        this.updateNavbar();
    }

    // 登出
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        this.updateNavbar();
    }

    // 更新导航栏
    updateNavbar() {
        const navbarUser = document.getElementById('navbar-user');
        if (!navbarUser) return;

        if (this.isLoggedIn()) {
            navbarUser.innerHTML = `
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" 
                       data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="fas fa-user"></i> ${this.user.username}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="auth.showProfile()">
                            <i class="fas fa-user-edit"></i> 个人资料
                        </a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="#" onclick="auth.logout(); window.location.href='/login';">
                            <i class="fas fa-sign-out-alt"></i> 退出登录
                        </a></li>
                    </ul>
                </li>
            `;
        } else {
            navbarUser.innerHTML = `
                <li class="nav-item">
                    <a class="nav-link" href="/login">
                        <i class="fas fa-sign-in-alt"></i> 登录
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/register">
                        <i class="fas fa-user-plus"></i> 注册
                    </a>
                </li>
            `;
        }
    }

    // 显示个人资料模态框
    showProfile() {
        if (!this.user) return;

        // 创建模态框HTML
        const modalHTML = `
            <div class="modal fade" id="profileModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-user-edit"></i> 个人资料
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="profileForm">
                                <div class="mb-3">
                                    <label for="profileUsername" class="form-label">用户名</label>
                                    <input type="text" class="form-control" id="profileUsername" 
                                           value="${this.user.username}" readonly>
                                </div>
                                <div class="mb-3">
                                    <label for="profileEmail" class="form-label">邮箱</label>
                                    <input type="email" class="form-control" id="profileEmail" 
                                           value="${this.user.email}" required>
                                </div>
                                <div class="mb-3">
                                    <small class="text-muted">
                                        注册时间: ${formatDateTime(this.user.created_at)}
                                    </small>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" onclick="auth.updateProfile()">保存</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 移除已存在的模态框
        const existingModal = document.getElementById('profileModal');
        if (existingModal) {
            existingModal.remove();
        }

        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('profileModal'));
        modal.show();
    }

    // 更新个人资料
    async updateProfile() {
        const email = document.getElementById('profileEmail').value;
        
        if (!validateEmail(email)) {
            showNotification('请输入有效的邮箱地址', 'error');
            return;
        }

        try {
            showLoading();
            const response = await axios.put('/api/auth/me', { email });
            
            // 更新本地用户信息
            this.user.email = response.data.email;
            localStorage.setItem('user_info', JSON.stringify(this.user));
            
            showNotification('个人资料更新成功', 'success');
            
            // 隐藏模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('profileModal'));
            modal.hide();
            
        } catch (error) {
            if (error.response && error.response.data && error.response.data.detail) {
                showNotification(error.response.data.detail, 'error');
            } else {
                showNotification('更新失败，请重试', 'error');
            }
        } finally {
            hideLoading();
        }
    }

    // 检查页面访问权限
    checkPageAccess() {
        const currentPath = window.location.pathname;
        const publicPaths = ['/', '/login', '/register'];
        
        if (!publicPaths.includes(currentPath) && !this.isLoggedIn()) {
            showNotification('请先登录', 'warning');
            window.location.href = '/login';
            return false;
        }
        
        return true;
    }

    // 验证管理员权限
    isAdmin() {
        return this.user && this.user.is_admin;
    }

    // 刷新用户信息
    async refreshUserInfo() {
        if (!this.token) return false;

        try {
            const response = await axios.get('/api/auth/me');
            this.user = response.data;
            localStorage.setItem('user_info', JSON.stringify(this.user));
            this.updateNavbar();
            return true;
        } catch (error) {
            console.error('Failed to refresh user info:', error);
            return false;
        }
    }
}

// 创建全局认证管理器实例
const auth = new AuthManager();

// 页面加载完成后检查访问权限
document.addEventListener('DOMContentLoaded', () => {
    auth.checkPageAccess();
});

// 导出到全局
window.auth = auth;