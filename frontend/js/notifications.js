// Notifications Management
const notificationsManager = {
    notifications: [],
    unreadCount: 0,
    eventSource: null,

    init() {
        this.loadNotifications();
        this.setupEventSource();
        this.setupUI();
    },

    setupUI() {
        const bell = document.getElementById('notificationBell');
        const dropdown = document.getElementById('notificationDropdown');
        
        bell.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
            if (dropdown.style.display === 'block') {
                this.markAllAsRead();
            }
        });
        
        document.addEventListener('click', () => {
            dropdown.style.display = 'none';
        });
    },

    setupEventSource() {
        // Utiliser Server-Sent Events pour recevoir les mises à jour en temps réel
        try {
            this.eventSource = new EventSource('/api/notifications/stream');
            this.eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.addNotification(data);
            };
            this.eventSource.onerror = () => {
                console.warn('SSE connection lost, will retry...');
                setTimeout(() => this.setupEventSource(), 5000);
            };
        } catch (e) {
            console.warn('SSE not supported, falling back to polling');
            // Fallback : polling toutes les 30 secondes
            setInterval(() => this.loadNotifications(), 30000);
        }
    },

    async loadNotifications() {
        try {
            const notifications = await api.getNotifications();
            this.notifications = notifications;
            this.unreadCount = notifications.filter(n => !n.read).length;
            this.updateUI();
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    },

    addNotification(notification) {
        this.notifications.unshift(notification);
        if (!notification.read) {
            this.unreadCount++;
        }
        this.updateUI();
        // Afficher un toast pour les notifications importantes
        if (notification.type === 'success' || notification.type === 'error') {
            showToast(notification.message, notification.type === 'success' ? 'success' : 'error', 8000);
        }
    },

    updateUI() {
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            badge.textContent = this.unreadCount;
            badge.style.display = this.unreadCount > 0 ? 'block' : 'none';
        }
        
        const list = document.getElementById('notificationList');
        if (list) {
            if (this.notifications.length === 0) {
                list.innerHTML = '<p style="padding: 12px; color: #666;">Aucune notification</p>';
            } else {
                list.innerHTML = this.notifications.slice(0, 20).map(n => `
                    <div class="notification-item ${n.read ? 'read' : 'unread'}" data-id="${n.id}">
                        <div class="notification-message">${n.message}</div>
                        <div class="notification-time">${new Date(n.created_at).toLocaleString()}</div>
                    </div>
                `).join('');
            }
        }
    },

    async markAllAsRead() {
        try {
            await api.markNotificationsRead();
            this.unreadCount = 0;
            this.notifications.forEach(n => n.read = true);
            this.updateUI();
        } catch (error) {
            console.error('Error marking notifications as read:', error);
        }
    }
};

// Initialize notifications
document.addEventListener('DOMContentLoaded', () => {
    notificationsManager.init();
});