// utils.js - Shared utilities, dynamic API and WebSocket resolving

// Resolve API & WS dynamically from current window location to prevent port conflicts!
var API_BASE = `${window.location.origin}/api`;
var WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

// Toast Notification System
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const textNode = document.createElement('span');
    textNode.textContent = message;
    toast.appendChild(textNode);
    
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.cssText = 'background:transparent; border:none; color:inherit; font-size:16px; margin-left:12px; cursor:pointer;';
    closeBtn.onclick = () => toast.remove();
    toast.appendChild(closeBtn);
    
    container.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 4000);
}

// Format date helper
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + d.toLocaleDateString();
    } catch {
        return dateStr;
    }
}
