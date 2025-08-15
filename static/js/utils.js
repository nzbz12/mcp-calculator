// 全局工具函数

// 显示通知
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notification-container');
    const alertClass = type === 'error' ? 'danger' : type;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${alertClass} alert-dismissible fade show notification`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // 自动消失
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

// 显示加载指示器
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

// 隐藏加载指示器
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化运行时间
function formatRuntime(seconds) {
    if (seconds < 60) return `${seconds}秒`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
    return `${(seconds / 3600).toFixed(1)}小时`;
}

// 获取状态徽章HTML
function getStatusBadge(status) {
    const statusMap = {
        'running': { class: 'status-running', text: '运行中', icon: 'fa-play' },
        'stopped': { class: 'status-stopped', text: '已停止', icon: 'fa-stop' },
        'starting': { class: 'status-starting', text: '启动中', icon: 'fa-hourglass-start' },
        'stopping': { class: 'status-stopping', text: '停止中', icon: 'fa-hourglass-end' },
        'error': { class: 'status-error', text: '错误', icon: 'fa-exclamation-triangle' }
    };
    
    const config = statusMap[status] || statusMap['stopped'];
    return `<span class="badge status-badge ${config.class}">
        <i class="fas ${config.icon}"></i> ${config.text}
    </span>`;
}

// 确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// 深拷贝对象
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 表单数据转换为JSON
function formDataToJSON(formData) {
    const object = {};
    formData.forEach((value, key) => {
        if (object[key]) {
            if (!Array.isArray(object[key])) {
                object[key] = [object[key]];
            }
            object[key].push(value);
        } else {
            object[key] = value;
        }
    });
    return object;
}

// 生成随机ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// 验证邮箱格式
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// 验证URL格式
function validateURL(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

// 复制到剪贴板
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('已复制到剪贴板', 'success');
        return true;
    } catch {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showNotification('已复制到剪贴板', 'success');
            return true;
        } catch {
            showNotification('复制失败', 'error');
            return false;
        } finally {
            document.body.removeChild(textArea);
        }
    }
}

// 文件拖拽处理
function setupFileDrop(element, callback) {
    element.addEventListener('dragover', (e) => {
        e.preventDefault();
        element.classList.add('dragover');
    });
    
    element.addEventListener('dragleave', (e) => {
        e.preventDefault();
        element.classList.remove('dragover');
    });
    
    element.addEventListener('drop', (e) => {
        e.preventDefault();
        element.classList.remove('dragover');
        const files = Array.from(e.dataTransfer.files);
        callback(files);
    });
}

// 模态框管理
class ModalManager {
    static show(modalId) {
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();
        return modal;
    }
    
    static hide(modalId) {
        const modalElement = document.getElementById(modalId);
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    }
}

// 表格排序
function sortTable(table, column, direction = 'asc') {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aVal = a.cells[column].textContent.trim();
        const bVal = b.cells[column].textContent.trim();
        
        // 尝试数字比较
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        // 字符串比较
        return direction === 'asc' 
            ? aVal.localeCompare(bVal) 
            : bVal.localeCompare(aVal);
    });
    
    tbody.innerHTML = '';
    rows.forEach(row => tbody.appendChild(row));
}

// 全局错误处理
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    if (!e.error.message.includes('Script error')) {
        showNotification('发生了一个错误，请刷新页面重试', 'error');
    }
});

// 网络状态监控
window.addEventListener('online', () => {
    showNotification('网络连接已恢复', 'success');
});

window.addEventListener('offline', () => {
    showNotification('网络连接已断开', 'warning');
});

// 页面可见性改变处理
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // 页面变为可见时，可以刷新数据
        const event = new CustomEvent('pageVisible');
        window.dispatchEvent(event);
    }
});

// 导出到全局
window.utils = {
    showNotification,
    showLoading,
    hideLoading,
    formatDateTime,
    formatFileSize,
    formatRuntime,
    getStatusBadge,
    confirmAction,
    deepClone,
    debounce,
    throttle,
    formDataToJSON,
    generateId,
    validateEmail,
    validateURL,
    copyToClipboard,
    setupFileDrop,
    ModalManager,
    sortTable
};